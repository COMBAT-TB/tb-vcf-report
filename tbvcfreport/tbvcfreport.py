"""Interface to CLI."""

import json
import os
import sys

import click
from snpit import snpit

try:
    from .report import generate_report
    from .vcfproc import VCFProc
except ImportError:
    from report import generate_report
    from vcfproc import VCFProc


def check_vcf(vcf_file):
    """Check vcf file for emptiness.

    :param vcf_file:
    :return:
    """
    _file = False
    if not vcf_file.endswith(".vcf"):
        click.echo(click.style(
            f"{vcf_file} is not a VCF file!\n", fg='red', bold=True))
    elif os.stat(vcf_file).st_size > 0 and vcf_file.endswith(".vcf"):
        _file = True
    else:
        sys.stderr.write(f"{vcf_file} is empty!\n")
    return _file


@click.group()
def cli():
    """Generate an HTML-based VCF report from SnpEff annotated VCF file(s)."""
    pass


@cli.command()
@click.option('--tbprofiler_report', type=click.File())
@click.argument('vcf_dir', type=click.Path(exists=True))
def generate(vcf_dir, tbprofiler_report=None):
    """Generate an interactive HTML-based report."""
    if os.path.isdir(vcf_dir):
        for root, dirs, files in os.walk(vcf_dir):
            if len(os.listdir(vcf_dir)) == 0:
                click.echo(click.style(
                    f"{vcf_dir} is empty!\n", fg='red', bold=True))
            for vcf_file in files:
                (base, ext) = os.path.splitext(vcf_file)
                vcf_file = os.path.join(os.path.abspath(vcf_dir), vcf_file)
                if check_vcf(vcf_file):
                    click.echo(click.style(
                        f"Processing {vcf_file}...\n", fg='green', bold=True))
                    file_name = vcf_file.split('/')[-1].split('.')[0]
                    # TODO: refactor to remove this code duplication
                    lineage_parser = snpit(input_file=vcf_file)
                    (species, lineage, sublineage,
                     percent_agreement) = lineage_parser.determine_lineage()
                    percent_agreement = round(percent_agreement)
                    vcf_file = VCFProc(vcf_file=vcf_file)
                    variants = vcf_file.parse()
                    rrs_start = 1471846
                    rrs_end = 1473382
                    call_positions = set()
                    rrs_variant_count = 0
                    for variant_record in variants:
                        POS = int(variant_record[17])
                        if POS >= rrs_start and POS <= rrs_end:
                            rrs_variant_count += 1
                        call_positions.add(POS)
                    generate_report(file_name=file_name, data={
                        'variants': variants,
                        'lineage': {
                            'species': species,
                            'lineage': lineage,
                            'sublineage': sublineage,
                            'percent_agreement': percent_agreement
                        },
                        'mixed_infection': False})
                # TODO: support generating DR reports for "directory mode"

    elif os.path.isfile(vcf_dir):
        vcf_file = os.path.abspath(vcf_dir)
        if check_vcf(vcf_file):
            file_name = vcf_file.split('/')[-1].split('.')[0]
            # TODO: refactor to remove this code duplication
            lineage_parser = snpit(input_file=vcf_file)
            (species, lineage, sublineage,
             percent_agreement) = lineage_parser.determine_lineage()
            percent_agreement = round(percent_agreement)
            vcf_file = VCFProc(vcf_file=vcf_file)
            variants = vcf_file.parse()
            rrs_start = 1471846
            rrs_end = 1473382
            call_positions = set()
            rrs_variant_count = 0
            for variant_record in variants:
                POS = int(variant_record[17])
                if POS >= rrs_start and POS <= rrs_end:
                    rrs_variant_count += 1
                call_positions.add(POS)
        if tbprofiler_report:
            tbprofiler_data = json.load(tbprofiler_report)
            dr_data = tbprofiler_data['dr_variants']

            drug_list = ['isoniazid', 'rifampicin', 'ethambutol',
                         'pyrazinamide', 'streptomycin', 'ethionamide',
                         'fluoroquinolones', 'amikacin', 'capreomycin',
                         'kanamycin', 'para-aminosalicylic_acid',
                         'cycloserine', 'delaminid', 'linezolid',
                         'clofazimine', 'bedaquiline'
                         ]
            drug_names = {
                'isoniazid': 'Isoniazid',
                'rifampicin': 'Rifampicin',
                'ethambutol': 'Ethambutol',
                'pyrazinamide': 'Pyrazinamide',
                'streptomycin': 'Streptomycin',
                'ethionamide': 'Ethionamide',
                'fluoroquinolones': 'Fluoroquinolones',
                'amikacin': 'Amikacin',
                'capreomycin': 'Capreomycin',
                'kanamycin': 'Kanamycin',
                'para-aminosalicylic_acid': 'Para-aminosalicylic acid',
                'linezolid': 'Linezolid',
                'cycloserine': 'Cycloserine',
                'delaminid': 'Delaminid',
                'clofazimine': 'Clofazimine',
                'bedaquiline': 'Bedaquiline'
            }
            drug_resistance = {}
            dr_calls_seen = set()
            for record in dr_data:
                drug_name = record['drug']
                if record['genome_pos'] in dr_calls_seen:
                    continue
                dr_calls_seen.add(record['genome_pos'])
                if drug_name not in drug_list:
                    print("Encountered unknown drug",
                          drug_name, file=sys.stderr)
                    continue
                dr_record = drug_resistance.get(drug_name, {
                    'drug': drug_name,
                    'drug_human_name': drug_names[drug_name],
                    'resistant': True,
                    'snippy_agreement': True, 'variants': []})
                if record['genome_pos'] not in call_positions:
                    dr_record['snippy_agreement'] = False
                dr_record['variants'].append((
                    record['gene'], record['change'], round(record['freq'], 2)
                ))
                drug_resistance[drug_name] = dr_record
            drug_resistance_list = []
            for drug_name in drug_names:
                if drug_name in drug_resistance:
                    drug_resistance_list.append(drug_resistance[drug_name])
                else:
                    drug_resistance_list.append({
                        'drug_name': drug_name,
                        'drug_human_name': drug_names[drug_name],
                        'resistant': False})
        else:
            drug_resistance_list = []
        generate_report(file_name=file_name, data={
            'variants': variants,
            'lineage': {
                'species': species,
                'lineage': lineage,
                'sublineage': sublineage,
                'percent_agreement': percent_agreement
            },
            'dr_data': drug_resistance_list,
            'mixed_infection': rrs_variant_count > 1})
    else:
        click.echo(click.style(
            f"Can't generate report for {vcf_dir}!\n", fg='red', bold=True))


if __name__ == '__main__':
    generate()
