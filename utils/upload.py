from flask_uploads import UploadSet, configure_uploads, IMAGES, patch_request_class

photos = UploadSet('photos', IMAGES)
