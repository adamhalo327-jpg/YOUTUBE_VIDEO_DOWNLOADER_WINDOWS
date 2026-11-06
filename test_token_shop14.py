import sqlite3
from pathlib import Path
from token_shop import PACKAGES,CloudTokenShop
from updates import newer

ROOT=Path(__file__).resolve().parents[1]

def test_packages_and_updates():
    assert PACKAGES['STARTER']=={'tokens':100,'days':1}
    assert PACKAGES['PRO']=={'tokens':500,'days':7}
    assert PACKAGES['ULTRA']=={'tokens':1500,'days':30}
    assert PACKAGES['PLUS']=={'tokens':250,'days':3}
    assert PACKAGES['LEGEND']=={'tokens':3000,'days':90}
    assert newer('14.0.1') and not newer('13.0.0')

def test_sql_migration_is_additive_and_reentrant():
    db=sqlite3.connect(':memory:')
    db.execute('PRAGMA foreign_keys=ON')
    old=(ROOT/'cloud_worker/token_shop_12_1_migration.sql').read_text()
    db.executescript(old)
    migration=(ROOT/'cloud_worker/token_shop_14_0_migration.sql').read_text()
    assert 'DROP TABLE' not in migration.upper()
    db.executescript(migration)
    db.executescript(migration)
    db.execute("INSERT INTO token_wallets VALUES ('wallet','hash','device','2026','ip','2026-11-06')")
    db.execute("INSERT INTO token_mission_claims14 VALUES ('m1','wallet','DAILY_3','2026-11-06',20,'now')")
    db.execute("INSERT OR IGNORE INTO token_mission_claims14 VALUES ('m2','wallet','DAILY_3','2026-11-06',20,'now')")
    assert db.execute('SELECT SUM(reward),COUNT(*) FROM token_mission_claims14').fetchone()==(20,1)
    db.execute("INSERT INTO token_purchases14 VALUES ('p1','wallet','PLUS',250,1000,'now')")
    assert db.execute('SELECT SUM(price) FROM token_purchases14').fetchone()==(250,)
    db.close()

def test_mission_methods_present():
    assert callable(CloudTokenShop.missions)
    assert callable(CloudTokenShop.claim_mission)
