import pyodbc


class SQL:
    def __init__(self, driver="Sql Server Native Client 11.0", server='DESKTOP-OLK7CR6', database="Ponisha"):
        self.connectionString = f"Driver={driver};" \
                               f"Server={server};" \
                               f"Database={database};" \
                               f"Trusted_connection=yes;"
        self.connection = None
        if self.connection is not None:
            self.disconnect()

    def connect(self):
        self.connection = pyodbc.connect(self.connectionString)

    def disconnect(self):
        self.connection.close()
