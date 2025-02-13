from methods.regular.regular_api import *
from shared.database.external.external import ExternalMap
from shared.database.task.job.user_to_job import User_To_Job


@routes.route('/api/v1/job/<int:job_id>/task/list', methods = ['POST'])
@Job_permissions.by_job_id(project_role_list = ["admin", "annotator", "Editor", "Viewer"], apis_user_list = ['builder_or_trainer'])
def task_list_by_job_api(job_id):
    with sessionMaker.session_scope() as session:
        spec_list = [{'date_from': None},
                     {'date_to': None},
                     {'status': None},
                     {'job_id': None},
                     {'all_my_jobs': {'required': False, 'kind': bool}},
                     {'project_string_id': None},
                     {'issues_filter': None},
                     {'project_id': {
                         'required': False,
                         'kind': int
                     }},
                     {'file_id': {
                         'required': False,
                         'kind': int
                     }},
                     {'page_number': {
                         'required': False,
                         'kind': int
                     }},
                     {'incoming_directory_id': None},
                     {'limit_count': {'required': False, 'kind': int, 'default': 25}},
                     {'mode_data': str}]

        log, input, untrusted_input = regular_input.master(request = request,
                                                           spec_list = spec_list)
        if len(log["error"].keys()) >= 1:
            return jsonify(log = log), 400
        job = Job.get_by_id(session, job_id)
        member = get_member(session)
        return _task_list_api(session = session, project_id = job.project.id, input = input, log = log, member = member)


@routes.route('/api/v1/project/<string:project_string_id>/task/list', methods = ['POST'])
@Project_permissions.user_has_project(["admin", "annotator", "Editor", "Viewer"])
def task_list_api(project_string_id):
    spec_list = [{'date_from': None},
                 {'date_to': None},
                 {'status': None},
                 {'page_number': None},
                 {'job_id': {'required': False, 'kind': int}},
                 {'all_my_jobs': {'required': False, 'kind': bool}},
                 {'issues_filter': None},
                 {'project_string_id': None},
                 {'project_id': {
                     'required': False,
                     'kind': int
                 }},
                 {'file_id': {
                     'required': False,
                     'kind': int
                 }},
                 {'incoming_directory_id': None},
                 {'limit_count': {'required': False, 'kind': int, 'default': 25}},
                 {'mode_data': str}]

    log, input, untrusted_input = regular_input.master(request = request,
                                                       spec_list = spec_list)
    with sessionMaker.session_scope() as session:
        if len(log["error"].keys()) >= 1:
            return jsonify(log = log), 400
        # For now we are not supporting querying the entire file list of a project.
        # So we check we have either a job ID or a FileID to filter with
        if input['file_id'] is None and input['job_id'] is None and input.get('all_my_jobs') is None:
            log['error']['file_id'] = 'Please Provide a file ID'
            log['error']['job_id'] = 'Please Provide a job ID'
            return jsonify(log = log), 400
        member = get_member(session)
        project = Project.get_by_string_id(session, project_string_id = project_string_id)
        return _task_list_api(session = session, project_id = project.id, input = input, log = log, member = member)


def _task_list_api(session, project_id, input = input, member = None, log = regular_log.default()):
    task_list, total_count = task_list_core(session = session,
                               date_from = input['date_from'],
                               date_to = input['date_to'],
                               status = input['status'],
                               job_id = input['job_id'],
                               all_my_jobs = input['all_my_jobs'],
                               incoming_directory_id = input['incoming_directory_id'],
                               project_id = project_id,
                               file_id = input['file_id'],
                               mode_data = input['mode_data'],
                               issues_filter = input['issues_filter'],
                               limit_count = input['limit_count'],
                               page_number = input.get('page_number'),
                               member = member)
    initial_dir_sync = None
    if input.get('job_id'):
        job = Job.get_by_id(session, input['job_id'])
        initial_dir_sync = job.pending_initial_dir_sync
        allow_reviews = job.allow_reviews
        log['success'] = True
        return jsonify(log = log,
                       task_list = task_list,
                       pending_initial_dir_sync = initial_dir_sync, allow_reviews = allow_reviews), 200

    return jsonify(log = log,
                   task_list = task_list,
                   total_count = total_count,
                   pending_initial_dir_sync = initial_dir_sync), 200


def get_external_id_to_task(session, task, task_template):
    if not task_template:
        return
    if not task_template.interface_connection:
        return
    connection = task_template.interface_connection
    if connection.integration_name == 'labelbox':
        # Try to find the task external ID
        external_map = ExternalMap.get(
            session = session,
            task_id = task.id,
            diffgram_class_string = "task",
            type = "labelbox",
        )
        if not external_map:
            return None
        return external_map.external_id


def task_list_core(session,
                   date_from,
                   date_to,
                   status,
                   job_id,
                   incoming_directory_id,
                   project_id,
                   file_id,
                   mode_data,
                   issues_filter,
                   all_my_jobs = False,
                   user_id = False,
                   member = None,
                   limit_count = 25,
                   page_number = 0):
    # if using time created

    if limit_count is None:
        limit_count = 25
    job_id_list = None
    user_id = None
    if member:
        user_id = member.user_id

    if all_my_jobs and user_id:
        job_id_list = User_To_Job.get_job_ids_from_user(session = session, user_id = user_id)

    task_list = Task.list(
        session = session,
        date_from = date_from,
        date_to = date_to,
        status = status,
        job_id = job_id,
        job_id_list = job_id_list,
        project_id = project_id,
        file_id = file_id,
        incoming_directory_id = incoming_directory_id,
        issues_filter = issues_filter,
        limit_count = limit_count,
        page_number = page_number,

    )
    total_tasks_count = Task.list(
        session = session,
        date_from = date_from,
        date_to = date_to,
        status = status,
        job_id = job_id,
        job_id_list = job_id_list,
        project_id = project_id,
        file_id = file_id,
        incoming_directory_id = incoming_directory_id,
        issues_filter = issues_filter,
        limit_count = None,
        page_number = None,
        return_mode = 'count'
    )

    out_list = []
    task_template = Job.get_by_id(session, job_id = job_id)

    for task in task_list:

        # TODO get builder vs trainer mode

        if mode_data == "exam_results":
            serialized = task.serialize_for_exam_results()
        else:
            serialized = task.serialize_for_list_view_builder(session = session, regen_url = False)
        external_id = get_external_id_to_task(session, task, task_template)
        if external_id:
            serialized['external_id'] = external_id
        out_list.append(serialized)

    return out_list, total_tasks_count
