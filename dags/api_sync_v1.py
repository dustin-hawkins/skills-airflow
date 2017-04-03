"""Workflow to sync saved CSV output data
to version 1 of the open skills API database
"""
import os
from datetime import datetime

from airflow.operators import BaseOperator

from config import config
from skills_ml.utils.airflow import datetime_to_year_quarter, datetime_to_quarter
from skills_ml.utils.db import get_apiv1_dbengine as get_db
from skills_ml.api_sync.v1.models import ensure_db

from skills_ml.api_sync.v1 import \
    load_jobs_master, \
    load_alternate_titles, \
    load_jobs_unusual_titles, \
    load_skills_master, \
    load_skills_importance, \
    load_geo_title_counts, \
    load_title_counts

from utils.dags import QuarterlySubDAG


default_args = {
    'depends_on_past': False,
    'start_date': datetime(2011, 1, 1),
}


def define_api_sync(main_dag_name):
    dag = QuarterlySubDAG(main_dag_name, 'api_v1_sync')

    output_folder = config.get('output_folder', 'output')

    table_files = {
        'jobs_master': 'job_titles_master_table.tsv',
        'skills_master': 'skills_master_table.tsv',
        'interesting_jobs': 'interesting_job_titles.tsv',
        'skill_importance': 'ksas_importance.tsv',
        'geo_title_count': 'geo_title_count_{}.csv',
        'title_count': 'title_count_{}.csv',
    }


    def full_path(filename):
        output_folder = os.environ.get('OUTPUT_FOLDER', None)
        if not output_folder:
            output_folder = config.get('output_folder', 'output')
        return os.path.join(output_folder, filename)


    class JobMaster(BaseOperator):
        def execute(self, context):
            engine = get_db()
            ensure_db(engine)
            load_jobs_master(full_path(table_files['jobs_master']), engine)


    class SkillMaster(BaseOperator):
        def execute(self, context):
            engine = get_db()
            ensure_db(engine)
            load_skills_master(full_path(table_files['skills_master']), engine)


    class JobAlternateTitles(BaseOperator):
        def execute(self, context):
            engine = get_db()
            ensure_db(engine)
            load_alternate_titles(full_path(table_files['jobs_master']), engine)


    class JobUnusualTitles(BaseOperator):
        def execute(self, context):
            engine = get_db()
            ensure_db(engine)
            load_jobs_unusual_titles(full_path(table_files['interesting_jobs']), engine)


    class SkillImportance(BaseOperator):
        def execute(self, context):
            engine = get_db()
            ensure_db(engine)
            load_skills_importance(full_path(table_files['skill_importance']), engine)


    class GeoTitleCounts(BaseOperator):
        def execute(self, context):
            year, quarter = datetime_to_year_quarter(context['execution_date'])
            quarter_string = datetime_to_quarter(context['execution_date'])
            engine = get_db()
            ensure_db(engine)
            load_geo_title_counts(
                filename=full_path(table_files['geo_title_count']).format(quarter_string),
                year=year,
                quarter=quarter,
                db_engine=engine,
            )


    class TitleCounts(BaseOperator):
        def execute(self, context):
            year, quarter = datetime_to_year_quarter(context['execution_date'])
            quarter_string = datetime_to_quarter(context['execution_date'])
            engine = get_db()
            ensure_db(engine)
            load_title_counts(
                filename=full_path(table_files['title_count']).format(quarter_string),
                year=year,
                quarter=quarter,
                db_engine=engine,
            )

    job_master = JobMaster(task_id='job_master', dag=dag)
    skill_master = SkillMaster(task_id='skill_master', dag=dag)
    alternate_titles = JobAlternateTitles(task_id='alternate_titles', dag=dag)
    unusual_titles = JobUnusualTitles(task_id='unusual_titles', dag=dag)
    skill_importance = SkillImportance(task_id='skill_importance', dag=dag)
    geo_title_counts = GeoTitleCounts(task_id='geo_title_counts', dag=dag)
    title_counts = TitleCounts(task_id='title_counts', dag=dag)

    alternate_titles.set_upstream(job_master)
    unusual_titles.set_upstream(job_master)
    skill_importance.set_upstream(job_master)
    skill_importance.set_upstream(skill_master)

    return dag
