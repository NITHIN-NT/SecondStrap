import multiprocessing

# Verify strictly that the bind address is correct for your environment
bind = "0.0.0.0:8000"

# Workers: suggested number is (2 x num_cores) + 1
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "gthread"
threads = 4

# Timeouts
timeout = 120
keepalive = 5

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Process naming
proc_name = "SecondStrapProject_gunicorn"

# Daemon mode (should be False for Docker/Supervisor)
daemon = False
