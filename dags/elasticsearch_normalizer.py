"""Index job postings

Take job postings from the common schema and index them along with
likely normalized job titles
"""

from airflow.operators import BaseOperator
from airflow.hooks import S3Hook

from skills_ml.utils.es import basic_client
from skills_ml.algorithms.elasticsearch_indexers.normalize_topn import NormalizeTopNIndexer
from skills_ml.utils.airflow import datetime_to_quarter
from skills_ml.datasets import job_postings
from config import config

from utils.dags import QuarterlySubDAG


def define_normalizer_index(main_dag_name):
    dag = QuarterlySubDAG(main_dag_name, 'normalize_elasticsearch')

    class IndexQuarterOperator(BaseOperator):
        def execute(self, context):
            conn = S3Hook().get_conn()
            quarter = datetime_to_quarter(context['execution_date'])
            NormalizeTopNIndexer(
                quarter=quarter,
                job_postings_generator=job_postings,
                job_titles_index=config['normalizer']['titles_master_index_name'],
                alias_name=config['normalizer']['es_index_name'],
                s3_conn=conn,
                es_client=basic_client()
            ).append()

    common_schema_quarterly = IndexQuarterOperator(task_id='common_schema_quarterly', dag=dag)

    return dag
