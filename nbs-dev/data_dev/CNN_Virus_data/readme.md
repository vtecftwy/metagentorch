### CNN Virus data (development directory version)

This directory includes a set of short data files used to test train and inference with the CNN Virus. 

#### File list and description:
##### 50-mer 
50-mer reads and their labels, in *text format* with one line per sample. Each line consists of three components, separated by tabs: the 50-mer read or sequence, the virus species label and the position label:
```text
'TTACNAGCTCCAGTCTAAGATTGTAACTGGCCTTTTTAAAGATTGCTCTA    94    5\n'
``` 
Files:

- `50mer_ds_100_seq`: small dataset with 100 reads
- `5train_short`: small 1000-read subset from the original training dataset for experiments
- `val_short`: small 500-read subset from the original validation dataset for experiments

##### 150-mer
150-mer reads and their labels in *text format* in a similar format as above:
```text
'TTCTTTCACCACCACAACCAGTCGGCCGTGGAGAGGCGTCGCCGCGTCTCGTTCGTCGAGGCCGATCGACTGCCGCATGAGAGCGGGTGGTATTCTTCCGAAGACGACGGAGACCGGGACGGTGATGAGGAAACTGGAGAGAGCCACAAC    6    0\n'
```
Files:

- `150mer_ds_100_reads`: small subset of 100 reads from original `ICTV_150mer_benchmarking` file

##### Other files:

- `virus_name_mapping`: mapping between virus species and their numerical label
- `weight_of_classes`:  weights for each virus species class in the training dataset

