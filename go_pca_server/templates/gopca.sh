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
EXPRESSION_FILE="expression.tsv"
GOPCA_FILE="gopca_result.pickle"
SIGNATURE_FILE="gopca_signatures.tsv"
SIGNATURE_EXCEL_FILE="gopca_signatures.xlsx"
SIGNATURE_MATRIX_FILE="gopca_signature_matrix.png"

DPI=150

echo "GO-PCA Run started!"

pushd "${DIR}" > /dev/null 2>&1

#touch SUCCESS
#popd > /dev/null 2>&1
#exit 0

#echo "Current working directory: `pwd`"

echo "Downloading expression file from {{expression_url}} ..."
if ! (curl -L -o "${EXPRESSION_FILE}" --max-filesize {{max_file_size}} "{{expression_url}}" > download_log.txt 2>&1); then
    echo "Download failed!"
    touch FAILURE
    exit 0
fi

echo "Generating list of protein-coding genes..."
if ! (gunzip -c "{{gene_annotation_file}}" | extract_protein_coding_genes.py -a - -s {{species_name}} -l extract_genes_log.txt \
        -o "${GENE_FILE}") ; then
    echo "Failed!"
    touch FAILURE
    exit 0
fi

echo "Generating GO annotation file..."
if ! gopca_extract_go_annotations.py -g "${GENE_FILE}" -t "{{gene_ontology_file}}" -a "{{go_association_file}}" -l extract_go_annotations_log.txt \
        -e ${EVIDENCE_STR} -o "${ANNOTATION_FILE}" --min-genes-per-term {{go_min_genes}} --max-genes-per-term {{go_max_genes}}; then
    echo "Failed!"
    touch FAILURE
    exit 0
fi

echo "Running GO-PCA..."
if ! (go-pca.py \
        -e "${EXPRESSION_FILE}" -a "${ANNOTATION_FILE}" -t "{{gene_ontology_file}}" \
        -G {{gopca_config.sel_var_genes}} -D {{gopca_config.n_components}} -P {{gopca_config.pval_thresh}} \
        --escore-pval-thresh {{gopca_config.escore_pval_thresh}} -E {{gopca_config.escore_thresh}} \
        --seed {{gopca_config.seed}} --pc-permutations {{gopca_config.pc_permutations}} --pc-zscore-thresh {{gopca_config.pc_zscore_thresh}} \
        -Xf {{gopca_config.mHG_X_frac}} -Xm {{gopca_config.mHG_X_min}} -L {{gopca_config.mHG_L}} \
        -R {{gopca_config.sig_corr_thresh}} -l gopca_log.txt {% if gopca_config.disable_local_filter %} --disable-local-filter {% endif %} {% if gopca_config.disable_global_filter %} --disable-global-filter {% endif %} \
        -o "${GOPCA_FILE}" > gopca_log.txt 2>&1); then
    echo "Failed!"
    touch FAILURE
    exit 0
fi

echo "Extracting signatures (as *.tsv file)..."
if ! (gopca_extract_signatures.py -g "${GOPCA_FILE}" -o "${SIGNATURE_FILE}"); then
    echo "Failed!"
    touch FAILURE
fi

echo "Extracting signatures (as *.xlsx file)..."
if ! (gopca_extract_signatures_excel.py -g "${GOPCA_FILE}" -o "${SIGNATURE_EXCEL_FILE}"); then
    echo "Failed!"
    touch FAILURE
fi

echo "Plotting signature matrix..."
if ! (gopca_plot_signature_matrix.py -g "${GOPCA_FILE}" -o "${SIGNATURE_MATRIX_FILE}" -r $DPI); then
    echo "Failed!"
    touch FAILURE
fi

touch SUCCESS

popd > /dev/null 2>&1

exit 0
