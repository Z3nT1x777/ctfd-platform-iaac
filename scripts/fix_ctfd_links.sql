UPDATE challenges SET connection_info = CONCAT('http://192.168.56.10/plugins/orchestrator/btn/', id, '?ttl_min=60');
SELECT id, name, connection_info FROM challenges;
