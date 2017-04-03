"""
Workflow to create labeled corpora
based on common schema job listings and available skills
"""
import csv
import logging
import os

from airflow.hooks import S3Hook
from airflow.operators import BaseOperator

from config import config
from skills_ml.datasets import job_postings
from skills_ml.utils.airflow import datetime_to_quarter
from skills_ml.utils.s3 import upload
from skills_ml.utils.hash import md5

from skills_ml.algorithms.corpus_creators.basic import SimpleCorpusCreator
from skills_ml.algorithms.skill_taggers.simple import SimpleSkillTagger

from utils.dags import QuarterlySubDAG


def define_skill_tag(main_dag_name):
    dag = QuarterlySubDAG(main_dag_name, 'skill_tag')

    output_folder = config.get('output_folder', 'output')
    if not os.path.isdir(output_folder):
        os.mkdir(output_folder)
    skills_filename = '{}/skills_master_table.tsv'.format(output_folder)

    class SkillTagOperator(BaseOperator):
        def execute(self, context):
            conn = S3Hook().get_conn()
            quarter = datetime_to_quarter(context['execution_date'])
            labeled_filename = 'labeled_corpora_a'
            with open(labeled_filename, 'w') as outfile:
                writer = csv.writer(outfile, delimiter='\t')
                job_postings_generator = job_postings(conn, quarter)
                corpus_generator = SimpleCorpusCreator()\
                    .raw_corpora(job_postings_generator)
                tagged_document_generator = \
                    SimpleSkillTagger(
                        skills_filename=skills_filename,
                        hash_function=md5
                    ).tagged_documents(corpus_generator)
                for document in tagged_document_generator:
                    writer.writerow([document])
            logging.info('Done tagging skills to %s', labeled_filename)
            upload(
                conn,
                labeled_filename,
                '{}/{}'.format(config['labeled_postings'], quarter)
            )

    SkillTagOperator(task_id='skill_tag', dag=dag)

    return dag
