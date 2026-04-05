from neo4j import GraphDatabase
from app.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
import logging

logger = logging.getLogger(__name__)

class Neo4jManager:
    """Singleton Neo4j connection manager for efficient connection pooling."""

    _instance = None
    _driver = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Neo4jManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._driver is None:
            try:
                self._driver = GraphDatabase.driver(
                    NEO4J_URI,
                    auth=(NEO4J_USER, NEO4J_PASSWORD),
                    max_connection_lifetime=30*60,  # 30 minutes
                    max_connection_pool_size=50,
                    connection_acquisition_timeout=60  # 60 seconds
                )
                logger.info("Neo4j connection pool initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Neo4j connection: {e}")
                raise

    @property
    def driver(self):
        """Get the Neo4j driver instance."""
        return self._driver

    def close(self):
        """Close the Neo4j driver connection."""
        if self._driver:
            self._driver.close()
            self._driver = None
            logger.info("Neo4j connection closed")

    def get_session(self):
        """Create a new Neo4j session from the driver."""
        if not self._driver:
            raise RuntimeError("Neo4j driver is not initialized")
        return self._driver.session()

    def verify_connection(self):
        """Verify the Neo4j connection is working."""
        try:
            with self._driver.session() as session:
                result = session.run("RETURN 'Connection OK' as status")
                record = result.single()
                return record["status"] == "Connection OK"
        except Exception as e:
            logger.error(f"Neo4j connection verification failed: {e}")
            return False

# Global singleton instance
neo4j_manager = Neo4jManager()