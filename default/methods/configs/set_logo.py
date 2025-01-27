try:
    from methods.regular.regular_api import *
except:
    from default.methods.regular.regular_api import *
from shared.permissions.super_admin_only import Super_Admin
from shared.data_tools_core import Data_tools
import uuid
import tempfile
from shared.database.image import Image
from shared.database.system_configs.system_configs import SystemConfigs
import mimetypes
data_tools = Data_tools().data_tools

@routes.route('/api/v1/admin/set-logo',
              methods = ['POST'])
@Super_Admin.is_super()
def api_admin_set_logo():
    log = regular_log.default()
    with sessionMaker.session_scope() as session:
        binary_file = request.files.get('file')
        if not binary_file:
            log['error']['file'] = 'No file provided'
            return jsonify(log = log), 400

        system_configs, log = admin_set_logo_core(session = session, file_binary = binary_file, log = log)
        if regular_log.log_has_error(log):
            return jsonify(log = log), 400

        return jsonify(sytem_configs = system_configs)
def admin_set_logo_core(session, file_binary, log = regular_log.default()):
    # Upload to temp dir
    temp_dir = tempfile.gettempdir()
    extension = file_binary.filename.split('.')[len(file_binary.filename.split('.')) - 1]
    allowed_formats = ['jpg', 'png', 'webp', 'jpeg']
    if extension not in allowed_formats:
        log['error']['image'] = f'Invalid image format only support {allowed_formats}.'
        return None, log
    file_path = f"{temp_dir}/{uuid.uuid4()}.{extension}"
    file_binary.save(file_path)
    blob_path = f'{settings.SYSTEM_DATA_BASE_DIR}{file_binary.filename}'
    # Upload to Cloud Storage

    content_type = mimetypes.guess_type(file_binary.filename)
    print('FILE PATH', file_path, content_type)
    data_tools.upload_to_cloud_storage(
        temp_local_path = file_path,
        blob_path = blob_path,
        content_type = content_type[0]
    )
    # Save new image Object
    new_image = Image(original_filename = file_binary.filename, url_signed_blob_path = blob_path)
    session.add(new_image)
    session.flush()
    # Save System Config
    config = SystemConfigs.set_logo(session = session, image_id = new_image.id)
    config_data = config.serialize(session = session)
    return config_data, log
