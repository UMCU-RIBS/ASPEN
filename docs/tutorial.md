## Create MySQL database
First create a database as root/admin (`mysql -u root -p`):

```SQL
CREATE DATABASE test;
GRANT ALL PRIVILEGES ON test.* TO 'giovanni'@'localhost';
FLUSH PRIVILEGES;
```

then, as a user, use this code (in bash):

```bash
cd tests/data/example/sql/
cat allowed_values.sql subjects.sql protocols.sql sessions.sql runs.sql channels.sql electrodes.sql recordings.sql files.sql extra_sessions.sql extra_runs.sql extra_recordings.sql > full.sql
mysql -u giovanni -p test' < full.sql
```

## Open the connection to the MySQL server

If the MySQL database is not stored in the local machine, you need to forward the local port of the remote database:

```bash
ssh -L 3306:localhost:3306 -o ServerAliveInterval=240 user@remote
```

## Connect to the database
To connect to the database (in localhost), you need to specify the `DATABASE_NAME`, the MySQL `USERNAME` and the MySQL `PASSWORD`.

```python
from xelo2.database.create import open_database
db = open_database('QMYSQL', DATABASE_NAME, USERNAME, PASSWORD)
```

## Look up MRI files for one subject
Here you can look up one of the files associated with the T1 of one subject. 
Specify the subject code in the `SUBJECT_CODE` as a string.

```python
from xelo2.bids.root import prepare_subset
from xelo2.api import Subject, Run

subj = Subject(db, code=SUBJECT_CODE)

main_search = f"`runs`.`task_name` = 't1_anatomy_scan' AND `subjects`.`id` = {subj.id}"
subset = prepare_subset(db, main_search)

for run_id in subset['runs']:
    run = Run(db, run_id)
    recs = run.list_recordings()
    if len(recs) == 0:
        print('no recordings for this run')
        
    rec = recs[0]
    files = rec.list_files()
    if len(files) == 0:
        print('no files for this run')
    
    file = files[0]
    print(file.path)
```
