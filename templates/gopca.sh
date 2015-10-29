{# This is the template for generating the GO-PCA script.

Arguments
---------
    species_name: the name of the species (e.g., human)

    gene_annotation_file: the (GTF) gene annotation file to use

#}
!/bin/bash

if ! (gunzip -c {{gene_annotation_file}} | extract_protein_coding_genes.py -a - -s {{species_name}} -l extract_genes_log.txt \
        > protein_coding_genes_{{species_name}}.tsv) ; then
    touch FAILURE
    exit 0
fi

touch SUCCESS
exit 0
