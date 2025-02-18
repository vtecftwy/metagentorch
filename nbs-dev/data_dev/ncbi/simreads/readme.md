### NCBI simulated reads
This directory includes all sets of simulated read sequence files generated from NCBI viral sequences using  ARC Illumina. 

```ascii
this-directory
    |--cov
    |    |
    |    |--single_10seq_50bp
    |    |    |--single_10seq_50bp.fq
    |    |    |--single_10seq_50bp.alnEnd
    |    |-- ...
    |    |--single_100seq_150bp
    |    |    |--single_100seq_150bp.fq
    |    |    |--single_100seq_150bp.aln
    |    |--paired_100seq_50bp
    |    |    |--paired_100seq_50bp2.aln
    |    |    |--paired_100seq_50bp1.aln
    |    |    |--paired_100seq_50bp2.fq
    |    |    |--paired_100seq_50bp1.fq
    |    |-- ...
    |    |
    |---yf
    |    |
    |    |--yf_AY968064-single-150bp
    |    |    |--yf_AY968064-single-1seq-150bp.fq
    |    |    |--yf_AY968064-single-1seq-150bp.aln
    |    |
    |--mRhiFer1
    |    |--mRhiFer1_v1.p.dna_rm.primary_assembly.1
    |    |    |--mRhiFer1_v1.p.dna_rm.primary_assembly.1.fq
    |    |    |--mRhiFer1_v1.p.dna_rm.primary_assembly.1.aln
    |    |

```

This directory includes several subdirectories, each for one virus, e.g. `cov` for corona, `yf` for yellow fever.

In each virus subdirectory, several simreads directory includes simulated reads with various parameters, named as `<method>_<nb-seq>_<nb-bp>` where"
- `<method>` is either `single` or `paired` depending on the simulation method
- `<nb-seq>` is the number of reference sequences used for simulation, and refers to the `fa` file used
- `<nb-bp>` is the number of base pairs used to simulate reads


Each sub-directory includes simreads files made using a simulation method and a specific number of reference sequences.
- `xxx.fq` and `xxx.aln` files when method is `single`
- `xxx1.fq`, `xxx2.fq`, `xxx1.aln` and `xxx2.aln` files when method is `paired`.

Example:
- `paired_10seq_50bp` means that the simreads were generated by using the `paired` method to simulate 50-bp reads, and using the `fa` file `cov_virus_sequences_010-seqs.fa`.
- `single_100seq_50bp` means that the simreads were generated by using the `single` method to simulate 50-bp reads, and using the `fa` file `cov_virus_sequences_100-seqs.fa`. Note that this generated 20,660,104 reads !

#### Simread file formats

Simulated reads information is split between two files:
- **FASTQ** (`.fq`) files providing the read sequences and their ASCII quality scores
- **ALN** (`.aln`) files with alignment information

##### FASTQ (`.fq`)
FASTQ files generated by ART Illumina have the following structure (showing 5 reads), with 4 lines for each read:

```ascii
@2591237:ncbi:1-60400
ACAACTCCTATTCGTAGTTGAAGTTGTTGACAAATACTTTGATTGTTACG
+
CCCBCGFGBGGGGGGGBGGGGGGGGG>GGG1G=/GGGGGGGGGGGGGGGG
@2591237:ncbi:1-60399
GATCAATGTGGCATCTACAATACAGACAGCATGAAGCACCACCAAAGGAC
+
BCBCCFGGGGGGGG1CGGGG<GGBGGGGGFGCGGGGGGDGGG/GG1GGGG
@2591237:ncbi:1-60398
ATCTACCAGTGGTAGATGGGTTCTTAATAATGAACATTATAGAGCTCTAC
+
CCCCCGGGEGG1GGF1G/GGEGGGGGGGGGGGGFFGGGGGGGGGGDGGDG
@2591237:ncbi:1-60397
CGTAAAGTAGAGGCTGTATGGTAGCTAGCACAAATGCCAGCACCAATAGG
+
BCCCCGGGFGGGGGGFGGGGFGG1GGGGGGG>GG1GGGGGGGGGGE<GGG
@2591237:ncbi:1-60396
GGTATCGGGTATCTCCTGCATCAATGCAAGGTCTTACAAAGATAAATACT
+
CBCCCGGG@CGGGGGGGGGGGG=GFGGGGDGGGFG1GGGGGGGG@GGGGG
```
The following information can be parsed from the each read sequence in the FASTQ file:

- Line 1: `readid`, a unique ID for the read, under for format `@readid` 
- Line 2: `readseq`, the sequence of the read
- Line 3: a separator `+`
- Line 4: `read_qscores`, the base quality scores encoded in ASCII 

Example:
```
@2591237:ncbi:1-60400
ACAACTCCTATTCGTAGTTGAAGTTGTTGACAAATACTTTGATTGTTACG
+
CCCBCGFGBGGGGGGGBGGGGGGGGG>GGG1G=/GGGGGGGGGGGGGGGG
```
- `readid` = `2591237:ncbi:1-60400`
- `readseq` = `ACAACTCCTATTCGTAGTTGAAGTTGTTGACAAATACTTTGATTGTTACG`, a 50 bp read
- `read_qscores` = `CCCBCGFGBGGGGGGGBGGGGGGGGG>GGG1G=/GGGGGGGGGGGGGGGG`


#### ALN (`.aln`) 
ALN files generated by ART Illumina consist of :
- a header with the ART-Ilumina command used for the simulation (`@CM`) and info on each of the reference sequences used for the simulations (`@SQ`). Header always starts with `##ART_Illumina` and ends with `##Header End` :
- the body with 3 lines for each read:
    1. definition line with `readid`, 
        - reference sequence identification number `refseqid`, 
        - the position in the read in the reference sequence `aln_start_pos` 
        - the strand the read was taken from `ref_seq_strand`. `+` for coding strand and `-` for template strand
    2. aligned reference sequence, that is the sequence segment in the original reference corresponding to the read
    3. aligned read sequence, that is the simmulated read sequence, where each bp corresponds to the reference sequence bp in the same position.

Example of a ALN file generated by ART Illumina (showing 5 reads):

```ascii
##ART_Illumina    read_length    50
@CM    /bin/art_illumina -i /home/vtec/projects/bio/metagentools/data/cov_data/cov_virus_sequences_ten.fa -ss HS25 -l 50 -f 100 -o /home/vtec/projects/bio/metagentools/data/cov_simreads/single_10seq_50bp/single_10seq_50bp -rs 1674660835
@SQ    2591237:ncbi:1 1   MK211378    2591237    ncbi    1     Coronavirus BtRs-BetaCoV/YN2018D    30213
@SQ    11128:ncbi:2   2   LC494191    11128    ncbi    2     Bovine coronavirus    30942
@SQ    31631:ncbi:3   3   KY967361    31631    ncbi    3     Human coronavirus OC43        30661
@SQ    277944:ncbi:4  4   LC654455    277944    ncbi    4     Human coronavirus NL63    27516
@SQ    11120:ncbi:5   5   MN987231    11120    ncbi    5     Infectious bronchitis virus    27617
@SQ    28295:ncbi:6   6   KU893866    28295    ncbi    6     Porcine epidemic diarrhea virus    28043
@SQ    28295:ncbi:7   7   KJ645638    28295    ncbi    7     Porcine epidemic diarrhea virus    27998
@SQ    28295:ncbi:8   8   KJ645678    28295    ncbi    8     Porcine epidemic diarrhea virus    27998
@SQ    28295:ncbi:9   9   KR873434    28295    ncbi    9     Porcine epidemic diarrhea virus    28038
@SQ    1699095:ncbi:10 10  KT368904    1699095    ncbi    10     Camel alphacoronavirus    27395
##Header End
>2591237:ncbi:1    2591237:ncbi:1-60400    14770    +
ACAACTCCTATTCGTAGTTGAAGTTGTTGACAAATACTTTGATTGTTACG
ACAACTCCTATTCGTAGTTGAAGTTGTTGACAAATACTTTGATTGTTACG
>2591237:ncbi:1    2591237:ncbi:1-60399    17012    -
GATCAATGTGGCATCTACAATACAGACAGCATGAAGCACCACCAAAGGAC
GATCAATGTGGCATCTACAATACAGACAGCATGAAGCACCACCAAAGGAC
>2591237:ncbi:1    2591237:ncbi:1-60398    9188    +
ATCTACCAGTGGTAGATGGGTTCTTAATAATGAACATTATAGAGCTCTAC
ATCTACCAGTGGTAGATGGGTTCTTAATAATGAACATTATAGAGCTCTAC
.....
```