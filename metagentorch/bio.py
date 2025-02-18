"""Information and simple tools related to genomics information"""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs-dev/03_bio.ipynb.

# %% auto 0
__all__ = ['q_score2prob_error', 'StandardDNACodon']

# %% ../nbs-dev/03_bio.ipynb 21
def q_score2prob_error(
    char:str,             # ASCII character retrieved from Q Score or Phred value in FASTQ
    ASCII_base:int=33     # ASCII base. Mostly 33, can be 64 in old FASTQ files
):
    """Return the probability of error for a given Q score encoded as ASCII character"""
    ASCII_code = ord(char)
    Q = ASCII_code - ASCII_base
    p_error = 10**(-Q/10)
    return p_error

# %% ../nbs-dev/03_bio.ipynb 35
class StandardDNACodon:
    """Hold standard DNA codon reference information
    
    1. DNA codon direct table: codon -> amino acid information
    2. DNA codin inverse table amino acid code (e.g. Cys) -> list of codons
    """
    # Technical note: this is a Singleton class
    # https://medium.com/geekculture/singleton-pattern-in-python-880e3feb622e 
    
    _db = [
        ('Ala', 'A','Alanine','GCT, GCC, GCA, GCG'),
        ('Arg', 'R','Arginine','CGT, CGC, CGA, CGG, AGA, AGG'),
        ('Asn', 'N','Asparagine','AAT, AAC'),
        # ('A'sn', B','Asn or Asp, B','AAT, AAC, GAT, GAC'),
        ('Asp', 'D','Aspartic acid','GAT, GAC'),
        ('Cys', 'C','Cysteine','TGT, TGC'),
        ('Gln', 'Q','Glutamine','CAA, CAG'),
        ('Glu', 'E','Glutamic acid','GAA, GAG'),
        # ('G'ln', Z','Glu or Glu, Z','CAA, CAG, GAA, GAG '),
        ('Gly', 'G','Glycine','GGT, GGC, GGA, GGG'),
        ('His', 'H','Histidine','CAT, CAC'),
        ('Ile', 'I','Isoleucine','ATT, ATC, ATA'),
        ('Leu', 'L','Leucine','CTT, CTC, CTA, CTG, TTA, TTG'),
        ('Lys', 'K','Lysine','AAA, AAG'),
        ('Met', 'M','Methionine','ATG'),
        ('Phe', 'F','Phenylalanine','TTT, TTC'),
        ('Pro', 'P','Proline','CCT, CCC, CCA, CCG'),
        ('Ser', 'S','Serine','TCT, TCC, TCA, TCG, AGT, AGC'),
        ('Thr', 'T','Threonine','ACT, ACC, ACA, ACG'),
        ('Trp', 'W','Tryptophan','TGG'),
        ('Tyr', 'Y','Tyrosine','TAT, TAC'),
        ('Val', 'V','Valine','GTT, GTC, GTA, GTG'),
        ('START','START', 'START','ATG'),
        ('STOP','STOP', 'STOP','TAA, TGA, TAG')
    ]
    
    __instance = None  
    
    def __new__(cls):
        """Create new instance if none exists, or return the one that exists"""
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
            # create the inverse table from the db
            cls.inverse_table = {s:{'amino acid name':n, 'amino acid letter': l, 'codons': c.split(', ')} 
                             for s, l, n, c in cls._db}
        return cls.__instance

    @property
    def direct_table(cls):
        dir_table = {} 
        for k, v in cls.inverse_table.items():
            for codon in v['codons']:
                subdict = {}
                subdict['amino acid symbol'] = k
                subdict['amino acid name'] = v['amino acid name']
                subdict['amino acid letter'] = v['amino acid letter']
                dir_table[codon] = subdict
        return dir_table
    
    @property
    def amino_acid_symbols(cls):
        return [s for s, l, n, c in cls._db]
    
    @property
    def amino_acid_names(cls):
        return [n for s, l, n, c in cls._db]
    
    @property
    def amino_acid_letters(cls):
        return [l for s, l, n, c in cls._db]
