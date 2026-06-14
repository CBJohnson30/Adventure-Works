import os
import pyodbc
import pandas as pd
from typing import Optional
from dotenv import load_dotenv
 
load_dotenv()


class AdventureWorksDB:
    """
    A simple database connector for AdventureWorks on SQL Server.
    Accepts a SQL query string and returns a pandas DataFrame.

    Usage:
        db = AdventureWorksDB()
        df = db.query("SELECT TOP 10 * FROM Production.WorkOrder")
        print(df.head())
    """

    def __init__(self):
        """
         Initialize the connector using environment variables from .env:
            DB_SERVER  — SQL Server instance
            DB_NAME    — Database name 
            DB_DRIVER  — ODBC driver 
        """
        self.server   = os.getenv("DB_SERVER")
        self.database = os.getenv("DB_NAME")
        self.driver   = os.getenv("DB_DRIVER")
        self.slackbot_username = os.getenv("SLACKBOT_USERNAME")
        self.slackbot_password = os.getenv("SLACKBOT_PASSWORD")
 
        if not all([self.server, self.database, self.driver,self.slackbot_username, self.slackbot_password]):
            raise EnvironmentError(
                "Missing one or more required environment variables: "
                "DB_SERVER, DB_NAME, DB_DRIVER, slackbot_username, slackbot_password "
                "Check your .env file."
            )
        
        self.connection_string = (
            f"DRIVER={{{self.driver}}};"
            f"SERVER={self.server};"
            f"DATABASE={self.database};"
            f"UID={self.slackbot_username};"
            f"PWD={self.slackbot_password};"
            "Trusted_Connection=yes;"  # Uses Windows Authentication
            "TrustServerCertificate=yes;"
        )

    def query(self, sql: str, params: Optional[tuple] = None) -> pd.DataFrame:
        """
        Execute a SQL query and return results as a pandas DataFrame.

        Args:
            sql:    A valid T-SQL query string
            params: Optional tuple of parameters for parameterized queries

        Returns:
            pd.DataFrame with query results, or empty DataFrame on failure

        Example:
            df = db.query("SELECT TOP 5 * FROM Production.WorkOrder")

            # With parameters:
            df = db.query(
                "SELECT * FROM Production.WorkOrder WHERE ScrappedQty > ?",
                params=(0,)
            )
        """
        try:
            with pyodbc.connect(self.connection_string) as conn:
                df = pd.read_sql(sql, conn, params=params)
                #print(f"Query returned {len(df)} rows and {len(df.columns)} columns.")
                return df

        except pyodbc.Error as e:
            print(f"Database error: {e}")
            return pd.DataFrame()

        except Exception as e:
            print(f"Unexpected error: {e}")
            return pd.DataFrame()

    def list_tables(self) -> pd.DataFrame:
        """
        Returns a DataFrame of all user tables in the database,
        grouped by schema. Useful for exploring AdventureWorks.
        """
        sql = """
            SELECT
                TABLE_SCHEMA AS Schema_Name,
                TABLE_NAME   AS Table_Name
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_SCHEMA, TABLE_NAME
        """
        return self.query(sql)
