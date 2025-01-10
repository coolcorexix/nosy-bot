# install dependencies

```
pip3 install -r requirements.txt
```

# run migrations
```
python migrations/run_migrations.py up   # to apply migrations
python migrations/run_migrations.py down # to rollback migrations
```

# on server
```
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/nosy_bot_prod\ 
path/to/venv/bin/pip3 install -r requirements.txt
```