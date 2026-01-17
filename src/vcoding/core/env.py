def has_docker_daemon() -> bool:
    """Check if Docker daemon is running."""
    import docker
    from docker.errors import DockerException

    try:
        client = docker.from_env()
        client.ping()
        return True
    except DockerException:
        return False
