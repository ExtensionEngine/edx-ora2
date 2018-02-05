import boto
import logging
from django.conf import settings

logger = logging.getLogger("openassessment.fileupload.api")

from .base import BaseBackend
from ..exceptions import FileUploadInternalError


class Backend(BaseBackend):

    def get_upload_url(self, key, content_type):
        bucket_name, key_name = self._retrieve_parameters(key)
        try:
            logger.info(bucket_name)
            logger.info(key_name)
            logger.info('Connecting to S3')
            conn = _connect_to_s3()
            logger.info('Connected to S3')
            logger.info('CORS configuration')
            bucket = conn.lookup(bucket_name)
            logger.info(bucket.get_cors())
            _set_cors_configuration(conn, bucket_name)

            upload_url = conn.generate_url(
                expires_in=self.UPLOAD_URL_TIMEOUT,
                method='PUT',
                bucket=bucket_name,
                key=key_name,
                headers={'Content-Length': '5242880', 'Content-Type': content_type}
            )
            return upload_url
        except Exception as ex:
            logger.exception(
                u"An internal exception occurred while generating an upload URL."
            )
            raise FileUploadInternalError(ex)


    def get_download_url(self, key):
        bucket_name, key_name = self._retrieve_parameters(key)
        try:
            conn = _connect_to_s3()
            bucket = conn.get_bucket(bucket_name)
            s3_key = bucket.get_key(key_name)
            return s3_key.generate_url(expires_in=self.DOWNLOAD_URL_TIMEOUT) if s3_key else ""
        except Exception as ex:
            logger.exception(
                u"An internal exception occurred while generating a download URL."
            )
            raise FileUploadInternalError(ex)


def _set_cors_configuration(conn, bucket_name):
    cors_cfg = boto.s3.cors.CORSConfiguration()
    cors_cfg.add_rule(['PUT', 'POST', 'DELETE'], 'https://{}'.format(settings.LMS_BASE),
                      allowed_header='*',
                      max_age_seconds=3000,
                      expose_header='x-amz-server-side-encryption')
    cors_cfg.add_rule('GET', '*')
    bucket = conn.lookup(bucket_name)
    bucket.set_cors(cors_cfg)
    logger.info('New CORS configuration')
    logger.info(bucket.get_cors())


def _connect_to_s3():
    """Connect to s3

    Creates a connection to s3 for file URLs.

    """
    # Try to get the AWS credentials from settings if they are available
    # If not, these will default to `None`, and boto will try to use
    # environment vars or configuration files instead.
    aws_access_key_id = getattr(settings, 'AWS_ACCESS_KEY_ID', None)
    aws_secret_access_key = getattr(settings, 'AWS_SECRET_ACCESS_KEY', None)
    aws_s3_host = getattr(settings, 'AWS_S3_HOST', None)

    return boto.connect_s3(
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        host=aws_s3_host
    )
