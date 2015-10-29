{# This is the template for generating the GO-PCA script.

Arguments
---------
    species_name: the name of the species (e.g., human)

    gene_annotation_file: the (GTF) gene annotation file to use

    gene_ontology_file: the (obo) gene ontology file
    go_association_file: the (GAF 2.0) GO association file
    evidence: the list of evidence codes passed to extract_go_annotations.py

#}#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

GENE_FILE="protein_coding_genes_{{species_name}}.tsv"
ANNOTATION_FILE="go_annotations_{{species_name}}.tsv"
EVIDENCE_STR="{% for e in go_evidence %} {{e}}{% endfor %}"

echo "GO-PCA Run started!"

pushd ${DIR} > /dev/null 2>&1

if ! (gunzip -c {{gene_annotation_file}} | extract_protein_coding_genes.py -a - -s {{species_name}} -l extract_genes_log.txt \
        -o ${GENE_FILE}) ; then
    touch FAILURE
    exit 0
fi

touch SUCCESS
popd > /dev/null 2>&1
exit 0

if ! gopca_extract_go_annotations.py -g "${GENE_FILE}" -t "{{gene_ontology_file}}" -a "{{go_association_file}}" \
        -e ${EVIDENCE_STR} -o "${ANNOTATION_FILE}" --min-genes-per-term {{go_min_genes}} --max-genes-per-term {{go_max_genes}}; then
    touch FAILURE
    exit 0
fi

touch SUCCESS

popd > /dev/null 2>&1

exit 0
