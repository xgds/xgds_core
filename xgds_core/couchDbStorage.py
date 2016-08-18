from django.conf import settings
from django.core.files.storage import Storage
from django.core.files import File
from django.core.exceptions import SuspiciousFileOperation
from django.utils.crypto import get_random_string
from django.utils.deconstruct import deconstructible
from django.core.urlresolvers import reverse

from datetime import datetime
import couchdb
import os.path
from io import BytesIO

@deconstructible
class CouchDbStorage(Storage):
    couchServer = None
    couchDb = None

    def __init__(self, database=None):
        self.setupComplete = False

    def _setupIfNeeded(self):
        if not self.setupComplete:
            self.couchServer = couchdb.Server()
            if database:
                self.couchDb = self.couchServer[database]
            else:
                self.couchDb = self.couchServer[settings.COUCHDB_FILESTORE_NAME]
            self.setupComplete = True

    def _open(self, name, mode='rb'):
        self._setupIfNeeded()
        doc = self.couchDb.get(name)
        if not doc:
            raise IOError("File not found in DB: %s" % name)
        directory, basename = os.path.split(name)
        attachment = self.couchDb.get_attachment(doc, basename)
        attachmentData = BytesIO(attachment.read())
        return File(attachmentData)

    def _save(self, name, content):
        self._setupIfNeeded()
        directory, basename = os.path.split(name)

        
        self.couchDb[name] = {"category":directory, "basename":basename,
                              "name": name, 
                              "creation_time":datetime.utcnow().isoformat()}
        doc = self.couchDb[name]
        content.seek(0)
        self.couchDb.put_attachment(doc, content, filename=basename)
        return name

    def delete(self, name):
        self._setupIfNeeded()
        doc = self.couchDb.get(name)
        if doc:
            self.couchDb.delete(doc)

    def exists(self, name):
        self._setupIfNeeded()
        return name in self.couchDb

    def size(self, name):
        self._setupIfNeeded()
        doc = self.couchDb.get(name)
        directory, basename = os.path.split(name)
        if not doc:
            raise IOError("File not found in DB: %s" % name)
        return doc["_attachments"][basename]["length"]

    def url(self, name):
        self._setupIfNeeded()
        directory, basename = os.path.split(name)
        return reverse("get_db_attachment", args=[directory, basename])

    def get_available_name(self, name, max_length=None):
        """
        Returns a filename that's free on the target storage system, and
        available for new content to be written to.
        """
        self._setupIfNeeded()
        dir_name, file_name = os.path.split(name)
        file_root, file_ext = os.path.splitext(file_name)
        # If the filename already exists, add an underscore and a random 7
        # character alphanumeric string (before the file extension, if one
        # exists) to the filename until the generated filename doesn't exist.
        # Truncate original name if required, so the new filename does not
        # exceed the max_length.
        while self.exists(name) or (max_length and len(name) > max_length):
            # file_ext includes the dot.
            name = os.path.join(dir_name, "%s_%s%s" % (file_root,
                                                       get_random_string(7), 
                                                       file_ext))
            if max_length is None:
                continue
            # Truncate file_root if max_length exceeded.
            truncation = len(name) - max_length
            if truncation > 0:
                file_root = file_root[:-truncation]
                # Entire file_root was truncated in attempt to find
                # an available filename.
                if not file_root:
                    raise SuspiciousFileOperation(
                        'Storage can not find an available filename for "%s". '
                        'Please make sure that the corresponding file field '
                        'allows sufficient "max_length".' % name
                    )
                name = os.path.join(dir_name, "%s_%s%s" % (file_root,
                                                           get_random_string(7),
                                                           file_ext))
        return name
