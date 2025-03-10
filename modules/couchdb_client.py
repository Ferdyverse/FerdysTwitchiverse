import couchdb
import config

class CouchDBClient:
    def __init__(self):
        self.server = couchdb.Server(config.COUCHDB_URL)

    def get_db(self, db_name):
        """Retrieve a specific database or create it if it does not exist."""
        if db_name not in self.server:
            return self.server.create(db_name)
        return self.server[db_name]

couchdb_client = CouchDBClient()
