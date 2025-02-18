"""Data preprocessing and transform tools for CNN Virus data."""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs-dev/03_cnn_virus_data.ipynb.

# %% auto 0
__all__ = ['CODE_ROOT', 'PACKAGE_ROOT', 'OriginalLabels', 'FastaFileReader', 'FastqFileReader', 'AlnFileReader',
           'TextFileDataset', 'AlnFileDataset', 'split_kmer_batch_into_50mers', 'combine_predictions',
           'combine_prediction_batch']

# %% ../../nbs-dev/03_cnn_virus_data.ipynb 3
import collections
import json
import os
import re
import warnings
from functools import partial, partialmethod
from pathlib import Path
from typing import Any, Optional

# %% ../../nbs-dev/03_cnn_virus_data.ipynb 4
# Set pytorch as backend
os.environ['KERAS_BACKEND'] = 'torch'

# %% ../../nbs-dev/03_cnn_virus_data.ipynb 5
import keras
import numpy as np
import pandas as pd
import torch
from eccore.core import safe_path, validate_path
from torch.utils.data import DataLoader, Dataset, IterableDataset
from tqdm.notebook import tqdm, trange

from ..bio import q_score2prob_error
from ..core import ProjectFileSystem, TextFileBaseReader

# %% ../../nbs-dev/03_cnn_virus_data.ipynb 6
# Retrieve the package root
from .. import __file__
CODE_ROOT = Path(__file__).parents[0]
PACKAGE_ROOT = Path(__file__).parents[1]

# %% ../../nbs-dev/03_cnn_virus_data.ipynb 22
class OriginalLabels:
    """Converts between labels and species name as per original training dataset"""
    def __init__(
        self, 
        p2mapping:Path|None = None   # Path to the mapping file. Uses `virus_name_mapping` by default
        ):
        if p2mapping is None:
            p2mapping = ProjectFileSystem().data / 'CNN_Virus_data/virus_name_mapping'
        else:
            p2mapping = safe_path(p2mapping)
        if not p2mapping.is_file(): raise FileNotFoundError(f"Mapping file not found at {p2mapping}")
        df = pd.read_csv(p2mapping, sep='\t', header=None, names=['species', 'label'])
        self._label2species = df['species'].to_list()
        self._label2species.append('Unknown Virus Species')
        self._species2label = {specie:label for specie, label in zip(df['species'], df['label'])}
        self._species2label['Unknown Virus Species'] = len(self._label2species)

    def search(self, s:str  # string to search through all original virus species
                       ):
        """Prints all species whose name contains the passed string, with their numerical label"""
        print('\n'.join([f"{k}. Label: {v}" for k,v in self._species2label.items() if s in k.lower()]))

    def label2species(self, n:int # label to convert to species name
                      ):
        """Converts a numerical label into the correpsonding species label"""
        return self._label2species[n]

    def species2label(self, s:str  # string to convert to label
                      ):
        """Converts a species name into the corresponding label number"""
        return self._species2label[s]

# %% ../../nbs-dev/03_cnn_virus_data.ipynb 43
class FastaFileReader(TextFileBaseReader):
    """Wrap a FASTA file and retrieve its content in raw format and parsed format"""
    def __init__(
        self,
        path: str|Path,  # path to the Fasta file
    ):
        super().__init__(path, nlines=1)
        self.text_to_parse_key = 'definition line'
        self.set_parsing_rules(verbose=False)
        
    def __next__(self)-> dict[str, str]:   # `{'definition line': text in dfn line, 'sequence': full sequence as str}` 
        """Return one definition line and the corresponding sequence"""
        lines = []
        for i in range(2):
            lines.append(self._safe_readline())
        dfn_line = lines[0].replace('\n', '')   #remove the next line symbol at the end of the line
        sequence = lines[1].replace('\n', '')   #remove the next line symbol at the end of the line
        self._chunk_nb = self._chunk_nb + 1
        return {'definition line':dfn_line, 'sequence':f"{sequence}"}

    @property
    def read_nb(self)-> int:
        return self._chunk_nb
    
    def print_first_chunks(
        self, 
        nchunks:int=3,  # number of chunks to print out
    ):
        """Print the first `nchunks` chunks of text from the file"""
        self.reset_iterator()
        for i, seq_dict in enumerate(self.__iter__()):
            print(f"\nSequence {i+1}:")
            print(seq_dict['definition line'])
            print(f"{seq_dict['sequence'][:80]} ...")
            if i >= nchunks-1: break
        self.reset_iterator()
            
    def parse_file(
        self,
        add_seq :bool=False,     # When True, add the full sequence to the parsed metadata dictionary
        save_json: bool=False    # When True, save the file metadata as a json file of same stem name
    )-> dict[str]:               # Metadata as Key/Values pairs
        """Read fasta file and return a dictionary with definition line metadata and optionally sequences"""
    
        self.reset_iterator()
        parsed = {}
        for d in self:
            dfn_line = d['definition line']
            seq = d['sequence']
            metadata = self._parse_text_fn(dfn_line, self.re_pattern)
            if add_seq: metadata['sequence'] = seq         
            parsed[metadata['seqid']] = metadata
                        
        if save_json:
            p2json = self.path.parent / f"{self.path.stem}_metadata.json"
            with open(p2json, 'w') as fp:
                json.dump(parsed, fp, indent=4)
                print(f"Metadata for '{self.path.name}'> saved as <{p2json.name}> in  \n{p2json.parent.absolute()}\n")

        return parsed

    def review(self):
        """Prints the first and last sequences and metadata in the fasta file and returns the nb or sequences"""

        self.reset_iterator()
        for i, seq in enumerate(self):
            if i == 0:
                first_dfn = seq['definition line']
                first_sequence = seq['sequence'][:80] + ' ...'
                first_meta = self.parse_text(seq['definition line'])
        print(f"There {'is' if i == 0 else 'are'} {i+1} sequences in this file")
        print('\nFirst Sequence:')
        print(first_dfn)
        print(first_sequence)
        print(first_meta)
        if i != 0:
            print('\nLast Sequence:')
            print(seq['definition line'])
            print(seq['sequence'][:80] + ' ...')
            print(self.parse_text(seq['definition line']))
        return i+1


# %% ../../nbs-dev/03_cnn_virus_data.ipynb 92
class FastqFileReader(TextFileBaseReader):
    """Iterator going through a fastq file's sequences and return each section + prob error as a dict"""
    def __init__(
        self,
        path:str|Path,   # path to the fastq file
    )-> dict:           # key/value with keys: definition line; sequence; q score; prob error
        self.nlines = 4
        super().__init__(path, nlines=self.nlines)
        self.text_to_parse_key = 'definition line'
        self.set_parsing_rules(verbose=False)        
    
    def __next__(self):
        """Return definition line, sequence and quality scores"""
        lines = []
        for i in range(self.nlines):
            lines.append(self._safe_readline().replace('\n', ''))
        
        output = {
            'definition line':lines[0], 
            'sequence':f"{lines[1]}", 
            'read_qscores': f"{lines[3]}",
        }
        output['probs error'] = np.array([q_score2prob_error(q) for q in output['read_qscores']])
        self._chunk_nb = self._chunk_nb + 1
        return output

    @property
    def read_nb(self)-> int:
        return self._chunk_nb
    
    def print_first_chunks(
        self, 
        nchunks:int=3,  # number of chunks to print out
    ):
        """Print the first `nchunks` chunks of text from the file"""
        for i, seq_dict in enumerate(self.__iter__()):
            print(f"\nSequence {i+1}:")
            print(seq_dict['definition line'])
            print(f"{seq_dict['sequence'][:80]} ...")
            if i >= nchunks: break
            
    def parse_file(
        self,
        add_readseq :bool=False,    # When True, add the full sequence to the parsed metadata dictionary
        add_qscores:bool=False,     # Add the read ASCII Q Scores to the parsed dictionary when True
        add_probs_error:bool=False, # Add the read probability of error to the parsed dictionary when True
        save_json: bool=False       # When True, save the file metadata as a json file of same stem name
    )-> dict[str]:                  # Metadata as Key/Values pairs
        """Read fastq file, return a dict with definition line metadata and optionally read sequence and q scores, ..."""
    
        self.reset_iterator()
        parsed = {}
        for d in self:
            dfn_line = d['definition line']
            seq, q_scores, prob_e = d['sequence'], d['read_qscores'], d['probs error']
            metadata = self._parse_text_fn(dfn_line, self.re_pattern, self.re_keys)
            if add_readseq: metadata['readseq'] = seq         
            if add_qscores: metadata['read_qscores'] = q_scores
            if add_probs_error: metadata['probs error'] = prob_e
            parsed[metadata['readid']] = metadata 
                        
        if save_json:
            p2json = self.path.parent / f"{self.path.stem}_metadata.json"
            with open(p2json, 'w') as fp:
                json.dump(parsed, fp, indent=4)
                print(f"Metadata for '{self.path.name}'> saved as <{p2json.name}> in  \n{p2json.parent.absolute()}\n")

        return parsed

# %% ../../nbs-dev/03_cnn_virus_data.ipynb 107
class AlnFileReader(TextFileBaseReader):
    """Iterator going through an ALN file"""
    def __init__(
        self,
        path:str|Path,   # path to the aln file
    )-> dict:            # key/value with keys: 
        """Set TextFileBaseReader attributes and specific class attributes"""
        self.nlines = 1
        super().__init__(path, nlines=self.nlines)
        self.header = self.read_header()
        self.nlines = 3
        self.text_to_parse_key = 'definition line'
        self.set_parsing_rules(verbose=False)
        self.set_header_parsing_rules(verbose=False)
        self.ref_sequences = self.parse_header_reference_sequences()

    def __next__(self):
        """Return definition line, sequence and quality scores"""
        lines = []
        for i in range(self.nlines):
            lines.append(self._safe_readline().replace('\n', ''))

        output = {
            'definition line':lines[0], 
            'ref_seq_aligned':f"{lines[1]}", 
            'read_seq_aligned': f"{lines[2]}",
        }   
        return output
    
    def read_header(self):
        """Read ALN file Header and return each section parsed in a dictionary"""
        
        header = {}
        if self.fp is not None:
            self.fp.close()
        self.fp = open(self.path, 'r')
        
        line = self._safe_readline().replace('\n', '')
        if not line.startswith('##ART_Illumina'): 
            raise ValueError(f"Header of this file does not start with ##ART_Illumina")
        line = self._safe_readline().replace('\n', '')
        if not line.startswith('@CM'): 
            raise ValueError(f"First header line should start with @CM")
        else: 
            header['command'] = line[3:].replace('\t', '').strip()

        refseqs = []
        while True:
            line = self._safe_readline().replace('\n', '')
            if line.startswith('##Header End'): break
            else:
                refseqs.append(line)
        header['reference sequences'] = refseqs
        
        return header
    
    def reset_iterator(self):
        """Reset the iterator to point to the first line in the file, by recreating a new file handle.
        
        `AlnFileReader` requires a specific `reset_iterator` method, in order to skip the header every time it is reset
        """
        if self.fp is not None:
            self.fp.close()
        self.fp = open(self.path, 'r')
        while True:
            line = self._safe_readline().replace('\n', '')
            if line.startswith('##Header End'): break

    def parse_definition_line_with_position(
        self, 
        dfn_line:str    # fefinition line string to be parsed
        )-> dict:       # parsed metadata in key/value format + relative position of the read
        """Parse definition line and adds relative position"""
        read_meta = self.parse_text(dfn_line)
        read_refseqid = read_meta['refseqid']
        read_start_pos = int(read_meta['aln_start_pos'])
        read_refseq_lentgh = int(self.ref_sequences[read_refseqid]['refseq_length'])
        read_meta['read_pos'] = (read_start_pos *10)// read_refseq_lentgh + 1
        return read_meta
    
    def parse_file(
        self, 
        add_ref_seq_aligned:bool=False,   # Add the reference sequence aligned to the parsed dictionary when True
        add_read_seq_aligned:bool=False,  # Add the read sequence aligned to the parsed dictionary when True
    )-> dict[str]: 
        # Key/Values. Keys: 
        # `readid`,`seqid`,`seq_nbr`,`read_nbr`,`aln_start_pos`,`ref_seq_strand`
        # optionaly `ref_seq_aligned`,`read_seq_aligned`
        """Read ALN file, return a dict w/ alignment info for each read and optionaly aligned reference sequence & read"""
        self.reset_iterator()
        parsed = {}
        for d in self:
            dfn_line = d['definition line']
            ref_seq_aligned, read_seq_aligned = d['ref_seq_aligned'], d['read_seq_aligned']
            metadata = self.parse_text(dfn_line)
            if add_ref_seq_aligned: metadata['ref_seq_aligned'] = ref_seq_aligned         
            if add_read_seq_aligned: metadata['read_seq_aligned'] = read_seq_aligned
            parsed[metadata['readid']] = metadata 
        return parsed

    def parse_header_reference_sequences(
        self,
        pattern:str|None=None,     # regex pattern to apply to parse the reference sequence info
        keys:list[str]|None=None,  # list of keys: keys are both regex match group names and corresponding output dict keys 
        )->dict[str]:                  # parsed metadata in key/value format
        """Extract metadata from all header reference sequences"""
        if pattern is None and keys is None:
            pattern, keys = self.re_header_pattern, self.re_header_keys
        parsed = {}
        for seq_dfn_line in self.header['reference sequences']:
            metadata = self.parse_text(seq_dfn_line, pattern, keys)
            parsed[metadata['refseqid']] = metadata
            
        return parsed       
        
    def set_header_parsing_rules(
        self,
        pattern: str|bool=None,   # regex pattern to apply to parse the text, search in parsing rules json if None
        keys: list[str]=None,     # list of keys/group for regex, search in parsing rules json if None
        verbose: bool=False       # when True, provides information on each rule
    )-> None:
        """Set the regex parsing rule for reference sequence in ALN header.
               
        Updates 3 class attributes: `re_header_rule_name`, `re_header_pattern`, `re_header_keys`
        
        TODO: refactor this and the method in Core: to use a single function for the common part and a parameter for the text_to_parse 
        """
        
        P2JSON = Path(f"{PACKAGE_ROOT}/default_parsing_rules.json")
        
        self.re_header_rule_name = None
        self.re_header_pattern = None
        self.re_header_keys = None
        
        # get the first reference sequence definition line in header
        text_to_parse = self.header['reference sequences'][0]
        divider_line = f"{'-'*80}"

        if pattern is not None and keys is not None:  # When specific pattern and keys are passed
            try:
                metadata_dict = self.parse_text(text_to_parse, pattern, keys)
                self.re_header_rule_name = 'Custom Rule'
                self.re_header_pattern = pattern
                self.re_header_keys = keys
                if verbose:
                    print(divider_line)
                    print(f"Custom rule was set for header in this instance.")
            except Exception as err: 
                raise ValueError(f"The pattern generates the following error:\n{err}")
                
        else:  # automatic rule selection among rules saved in json file
            # Load all existing rules from json file
            with open(P2JSON, 'r') as fp:
                parsing_rules = json.load(fp)
                
            # test all existing rules and keep the one with highest number of matches
            max_nbr_matches = 0
            for k, v in parsing_rules.items():
                re_header_pattern = v['pattern']
                re_header_keys = v['keys'].split(' ')
                try:
                    metadata_dict = self.parse_text(text_to_parse, re_header_pattern, re_header_keys)
                    nbr_matches = len(metadata_dict)
                    if verbose:
                        print(divider_line)
                        print(f"Rule <{k}> generated {nbr_matches:,d} matches")
                        print(divider_line)
                        print(re_header_pattern)
                        print(re_header_keys)

                    if len(metadata_dict) > max_nbr_matches:
                        self.re_header_pattern = re_header_pattern
                        self.re_header_keys = re_header_keys
                        self.re_header_rule_name = k    
                except Exception as err:
                    if verbose:
                        print(divider_line)
                        print(f"Rule <{k}> generated an error")
                        print(err)
                    else:
                        pass
            if self.re_header_rule_name is None:
                msg = """
        None of the saved parsing rules were able to extract metadata from the first line in this file.
        You must set a custom rule (pattern + keys) before parsing text, by using:
            `self.set_parsing_rules(custom_pattern, custom_list_of_keys)`
                """
                warnings.warn(msg, category=UserWarning)
            
            if verbose:
                print(divider_line)
                print(f"Selected rule with most matches: {self.re_header_rule_name}")

            # We used the iterator, now we need to reset it to make all lines available
            self.reset_iterator()

# %% ../../nbs-dev/03_cnn_virus_data.ipynb 144
class TextFileDataset(IterableDataset):
    """Load data from text file and yield (BHE sequence tensor, (label OHE tensor, position OHE tensor))"""

    base2encoding = {
        'A': [1,0,0,0,0], 
        'C': [0,1,0,0,0], 
        'G': [0,0,1,0,0], 
        'T': [0,0,0,1,0], 
        'N': [0,0,0,0,1],
        '-': [0,0,0,0,1],
        }
    nb_labels = 187
    nb_pos = 10
    
    def __init__(
        self,
        p2file:str|Path,  # path to the file to read
    ):
        self.p2file = safe_path(p2file)

    def __iter__(self):
        with open(self.p2file, 'r') as f:
            for line in f:
                # wi = torch.utils.data.get_worker_info()
                # if wi:
                #     print(f"{wi.id} loading {line}")
                seq, lbl, pos = line.replace('\n','').strip().split('\t')
                seq_bhe = torch.tensor(list(map(self._bhe_fn, seq)))
                lbl_ohe = torch.zeros(self.nb_labels)
                lbl_ohe[int(lbl)] = 1
                pos_ohe = torch.zeros(self.nb_pos)
                pos_ohe[int(pos)] = 1
                yield seq_bhe, (lbl_ohe, pos_ohe)
    
    def _bhe_fn(self, base:str) -> list[int]:
        """Convert a base to a one hot encoding vector"""
        return self.base2encoding[base]

# %% ../../nbs-dev/03_cnn_virus_data.ipynb 153
class AlnFileDataset(IterableDataset):
    """Load data and metadata from ALN file, yield BHE sequence, OHE label, OHE position tensors + metadata

    The iterator yield tupple (read tensor,(label tensor, position tensor)):
    
    - kmer read tensor in base hot encoded format (shape [k, 5])
    - label tensor in one hot encoded format (shape [187])
    - position tensor in one hote encoded format (shape [10])

    It also optionally returns a dictionary of the read metadata available in the ALN file.
    """

    base2encoding = {
        'A': [1,0,0,0,0], 
        'C': [0,1,0,0,0], 
        'G': [0,0,1,0,0], 
        'T': [0,0,0,1,0], 
        'N': [0,0,0,0,1],
        '-': [0,0,0,0,1],
        }
    nb_labels = 187
    nb_pos = 10
    
    def __init__(
        self,
        p2file:str|Path,            # path to the file to read
        label:int = 118,            # label for this batch (assuming all reads are from the same species)
        return_metadata:bool=False  # yield each read metadata as a dictionary when Trud
    ):
        self.p2file = safe_path(p2file)
        self.aln = AlnFileReader(self.p2file)
        self.label = label
        self.return_metadata = return_metadata

    def __iter__(self):
        for d in self.aln:
            metadata = self.aln.parse_definition_line_with_position(d['definition line'])
            seq = d['read_seq_aligned']
            seq_bhe = torch.tensor(list(map(self._bhe_fn, seq)))
            lbl_ohe = torch.zeros(self.nb_labels)
            lbl_ohe[int(self.label)] = 1
            pos = metadata['read_pos']
            pos_ohe = torch.zeros(self.nb_pos)
            pos_ohe[int(pos-1)] = 1
            if self.return_metadata:
                yield seq_bhe, (lbl_ohe, pos_ohe), metadata
            else:   
                yield seq_bhe, (lbl_ohe, pos_ohe)
    
    def _bhe_fn(self, base:str) -> list[int]:
        """Convert a base to a one hot encoding vector"""
        return self.base2encoding[base]

# %% ../../nbs-dev/03_cnn_virus_data.ipynb 162
def split_kmer_batch_into_50mers(
    kmer_b: torch.Tensor ,                      # tensor representing a batch of k-mer reads, BHE format, shape [b, k, 5]
    labels: tuple[torch.Tensor, torch.Tensor]|None = None,    # optional tuple with tensor for label and position batches
    ) -> tuple[torch.Tensor,tuple]: # batch tensor for 50-mer reads, (optional) labels and positions batch tensor
    """Convert a batch of k-mer reads into 50-mer reads, by shifting the k-mer one base at a time.

    Shapes: 
    
      - kmer_b:             [b,k,5]         ->  [b * (k - 49), 50, 5]
      - label/position_b:   [b, nb_class]   ->  [b * (k - 49), nb_class]

    Technical Note: we use advanced indexing of the tensor to create the 50-mer and roll them, with no loop.
    """
    b = kmer_b.shape[0]
    k = kmer_b.shape[1]
    n = k - 49

    # Verify inputs
    if labels is None:
        handle_reads_only = True
    else:
        handle_reads_only = False
        if len(labels) != 2:
            raise ValueError(f"labels must be a tuple of 2 tensors, got {len(labels)}")
        label_b, position_b = labels
        if label_b.shape[0] != b:
            raise ValueError(f"label batch has shape {label_b.shape}, expected {b}")
        if position_b.shape[0] != b:
            raise ValueError(f"position batch has shape {position_b.shape}, expected {b}")

    # Handle batch or k-mer reads    

    # Create an array of indices for rolling
    idx_rows = np.arange(n)[:, None]    # shape (n, 1) broadcast n rows to create the split effect
    idx_bases = np.arange(k)            # shape (k) creates the shifting effect
    indices = idx_rows + idx_bases      # shape (n, k)
    rolled_indices = indices  % k       # shape (n, k) Modulo to create the rolling effect

    # Create a rolled tensor using broadcasting
    rolled_tensor = kmer_b[:, rolled_indices, :].reshape(-1,k, 5)

    # Handle labels and positions
    if handle_reads_only:
        return rolled_tensor[:, :50,:],(torch.empty(0),torch.empty([b*n, 10]))
    else:
        label_b = label_b.repeat_interleave(n, dim=0)
        position_b = position_b.repeat_interleave(n, dim=0)
        return rolled_tensor[:, :50,:], (label_b, position_b)

# %% ../../nbs-dev/03_cnn_virus_data.ipynb 182
def combine_predictions(
    label_probs: torch.Tensor,              # Probabilities for the labels classes for each 50-mer (shape: [bs, k-49,187])
    pos_probs: torch.Tensor,                # Probabilities for the position classes for each 50-mer (shape: [bs, k-49,10])
    threshold: float = 0.9,                  # Threshold to consider a prediction as valid
    ) -> tuple[torch.Tensor, torch.Tensor]: # Predicted labels and positions for each read (shape: [bs, 187], [bs, 10])
    """Combine a batch of 50-mer probabilities into one batch of final prediction for label and position

    Note: the input must be of shape (batch_size, n, c) where n is k-49 and c is the nb of labels or positions
    """
    INVALID = 9999
    is_batch = True
    
    assert label_probs.dim() == pos_probs.dim(), "Input do not have the same nb of dimensions"

    if label_probs.dim() != 3:
        print('Converting probability tensors to 3 dimensions')
        label_probs = label_probs.unsqueeze(0)
        pos_probs = pos_probs.unsqueeze(0)

    # Extract the prediction for each 50-mer read
    label_preds = label_probs.argmax(dim=2) # shape (bs, nb_50mers)
    pos_preds = pos_probs.argmax(dim=2)
    # print(label_preds.shape, pos_preds.shape, label_probs.shape, pos_probs.shape)

    # Identify reads with too low prediction probability and replace their prediction by INVALID
    invalid_labels_filter = label_probs.max(dim=2).values <= threshold
    # print(invalid_labels_filter.shape)
    label_preds[invalid_labels_filter] = INVALID
    pos_preds[invalid_labels_filter] = INVALID

    def most_common_value(preds, invalid_filter):
        # print(f"_preds {preds.shape}:\n",preds)
        # Get unique values and their counts for the entire tensor
        unique_values, inverse_indices = torch.unique(preds, return_inverse=True)
        inverse_indices = inverse_indices.view(preds.shape)
        # print(f"unique_values {unique_values.shape}:\n",unique_values)
        # print(f"inverse_indices {inverse_indices.shape}:\n",inverse_indices)

        # Create a tensor to hold the counts (shape (bs, nb_unique_values_across_the_batch))
        counts = torch.zeros((preds.shape[0], unique_values.shape[0]), dtype=torch.int64)
        # Count occurrences of each unique value per row
        counts.scatter_add_(dim=1, index=inverse_indices, src=torch.ones_like(inverse_indices, dtype=torch.int64))
        # print(f"counts {counts.shape}:\n", counts)

        # get value most voted per 50-read (vertical tensor), excluding the placeholder INVALID
        most_voted_value = unique_values[counts[:, :-1].argmax(dim=1)][:, None]
        # print(f"most_voted_value {most_voted_value.shape}:\n", most_voted_value)
        return most_voted_value

    combined_labels = most_common_value(label_preds, invalid_labels_filter)
    combined_pos = most_common_value(pos_preds, invalid_labels_filter)

    return combined_labels.squeeze(), combined_pos.squeeze()

# %% ../../nbs-dev/03_cnn_virus_data.ipynb 189
def combine_prediction_batch(*args, **kwargs):
    """Deprecated"""
    msg = """
    `combine_prediction_batch` is deprecated. 
    Use `combine_predictions` instead, with same capabilities and more."""
    raise DeprecationWarning(msg)
