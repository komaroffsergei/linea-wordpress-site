"""Install a new author demo. Requires Docker Compose and initialized Git submodules."""
from pathlib import Path
import json,secrets,subprocess,time,urllib.request

ROOT=Path(__file__).resolve().parent
SITE=json.loads((ROOT/'site.json').read_text(encoding='utf-8'))
def run(args,check=True,inp=None):
 p=subprocess.run(args,cwd=ROOT,input=inp,capture_output=True,text=True)
 if check and p.returncode:raise RuntimeError('Command failed: '+str(args[:3])+' '+p.stderr[:350])
 return p
def main():
 if not (ROOT/'theme/style.css').exists() or not (ROOT/'plugins/komaroff-demo/komaroff-demo.php').exists():
  raise SystemExit('Run git submodule update --init --recursive first.')
 envfile=ROOT/'.env'
 values={'DB_ROOT_PASSWORD':secrets.token_hex(24),'DB_PASSWORD':secrets.token_hex(24),'ADMIN_PASSWORD':secrets.token_hex(20),'ADMIN_USER':'portfolio_admin','ADMIN_EMAIL':'demo@example.invalid','SITE_URL':'http://localhost:'+str(SITE['port']),'PORT':str(SITE['port'])}
 if envfile.exists():values.update(dict(line.split('=',1) for line in envfile.read_text(encoding='utf-8').splitlines() if line and not line.startswith('#') and '=' in line))
 envfile.write_text(''.join(k+'='+v+'\n' for k,v in values.items()),encoding='utf-8')
 try:envfile.chmod(0o600)
 except OSError:pass
 run(['docker','compose','up','-d'])
 cache=ROOT/'.cache';cache.mkdir(exist_ok=True);cli=cache/'wp-cli.phar'
 if not cli.exists():urllib.request.urlretrieve('https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar',cli)
 run(['docker','compose','cp',str(cli),'wordpress:/tmp/wp-cli.phar'])
 def wp(args,check=True,inp=None):return run(['docker','compose','exec','-T','-u','www-data','wordpress','php','/tmp/wp-cli.phar']+args,check,inp)
 for _ in range(60):
  probe="try{$db=new mysqli(getenv('WORDPRESS_DB_HOST'),getenv('WORDPRESS_DB_USER'),getenv('WORDPRESS_DB_PASSWORD'),getenv('WORDPRESS_DB_NAME'));exit($db->connect_errno?1:0);}catch(Throwable $e){exit(1);}"
  if run(['docker','compose','exec','-T','wordpress','php','-r',probe],False).returncode==0 and wp(['core','version'],False).returncode==0:break
  time.sleep(1)
 else:raise RuntimeError('WordPress database did not become ready')
 if wp(['core','is-installed'],False).returncode:
  wp(['core','install','--url='+values['SITE_URL'],'--title='+SITE['title'],'--admin_user='+values['ADMIN_USER'],'--admin_email='+values['ADMIN_EMAIL'],'--skip-email','--prompt=admin_password'],inp=values['ADMIN_PASSWORD']+'\n')
 wp(['language','core','install','ru_RU']);wp(['site','switch-language','ru_RU'])
 wp(['plugin','delete','hello','akismet'],False)
 if SITE['slug']=='forma':wp(['plugin','install','woocommerce','--version=11.2.2','--activate'])
 wp(['plugin','activate','komaroff-demo']);wp(['theme','activate','komaroff-'+SITE['slug']])
 # Seed refuses to repeat a completed import; use it only in this new demo installation.
 wp(['eval-file','wp-content/plugins/komaroff-demo/seed.php',SITE['slug']])
 if SITE['slug']=='forma':
  for k,v in {'woocommerce_currency_pos':'right_space','woocommerce_price_num_decimals':'0','woocommerce_price_thousand_sep':' '}.items():wp(['option','update',k,v])
 wp(['rewrite','structure','/%postname%/','--hard']);wp(['core','verify-checksums'])
 print('Demo ready: '+values['SITE_URL']+' | Admin password is stored locally in .env; never commit it.')
if __name__=='__main__':main()
