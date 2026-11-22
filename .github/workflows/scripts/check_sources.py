"""Conservative official-site change monitor.

Runs in GitHub Actions every six hours. Does NOT overwrite verified admissions
facts: only updates a separate, clearly labeled, unverified change feed.
"""
from __future__ import annotations
import concurrent.futures
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urldefrag
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / 'data/schools.json'
STATE_FILE = ROOT / 'data/source_state.json'
OUT_FILE = ROOT / 'docs/data/monitor.json'
NOW = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
UA = 'Mozilla/5.0 (compatible; AdmissionsNoticeMonitor/1.0; +https://github.com/)'
KEYWORDS = re.compile(r'(2027.{0,45}博[士生]|博[士生].{0,45}2027)')


def permitted(url):
    try:
        u=urlsplit(url)
        host=(u.hostname or '').lower()
        return u.scheme in ('http','https') and (host.endswith('.edu.cn') or host.endswith('.ac.cn'))
    except ValueError:
        return False


def canon(url):
    return urldefrag(url)[0]


def normalize(s):
    s=re.sub(r'(阅读量|访问量|浏览次数|点击数|点击率|阅读次数)[：:\s]*\d+', '', s)
    s=re.sub(r'\s+', ' ', s)
    return s.strip()


def check(page):
    school,url=page['school'],page['url']
    if not permitted(url):
        return {'url':url,'schoolId':school['id'],'schoolName':school['name'],'error':'站点不是学校官方教育域名'}
    try:
        resp=requests.get(url,headers={'User-Agent':UA,'Accept-Language':'zh-CN,zh;q=0.9,en;q=0.5'},timeout=18,allow_redirects=True)
        resp.raise_for_status()
        if not permitted(resp.url):
            raise ValueError('页面跳转到非教育机构域名')
        content_type=resp.headers.get('content-type','')
        if 'text/html' not in content_type and 'text/plain' not in content_type and not resp.text.lstrip().startswith('<'):
            raise ValueError('返回非HTML内容')
        resp.encoding=resp.apparent_encoding if resp.apparent_encoding else resp.encoding
        soup=BeautifulSoup(resp.text,'html.parser')
        title=normalize((soup.title.get_text(' ',strip=True) if soup.title else url))[:150]
        main=soup.select_one('article,.v_news_content,.wp_articlecontent,#vsb_content,.article-content,.article,.content,main') or soup.body or soup
        for child in main.select('script,style,nav,header,footer,form,iframe,.breadcrumb,.copyright,.share,.page-footer'):
            child.decompose()
        txt=normalize(main.get_text(' ',strip=True))
        if len(txt)<80:
            raise ValueError('提取到的文本过少，可能是登录页或动态渲染页面')
        if ('网站维护' in txt and len(txt)<600) or ('验证码' in txt and len(txt)<400):
            raise ValueError('页面疑似维护/验证码')
        digest=hashlib.sha256(txt[:35000].encode('utf-8')).hexdigest()
        links={}
        for a in soup.find_all('a',href=True):
            label=normalize(a.get_text(' ',strip=True))[:160]
            target=canon(urljoin(resp.url,a.get('href','')))
            if label and KEYWORDS.search(label) and permitted(target):
                links[target]=label
        return {'url':url,'schoolId':school['id'],'schoolName':school['name'],
                'title':title,'hash':digest,'links':links,'checkedAt':NOW}
    except Exception as ex:
        return {'url':url,'schoolId':school['id'],'schoolName':school['name'],
                'error':str(ex)[:220], 'checkedAt':NOW}


def load(path,default):
    try: return json.loads(path.read_text(encoding='utf-8'))
    except (OSError,json.JSONDecodeError): return default


def main():
    schools=load(DATA_FILE,{}).get('schools',[])
    old=load(STATE_FILE,{'pages':{},'recentChanges':[],'recentDiscovered':[]})
    old_pages=old.get('pages',{})
    pages=[{'school':s,'url':url} for s in schools for url in list(dict.fromkeys(s.get('monitorUrls',[]))) if permitted(url)]
    print('Checking',len(pages),'official URLs for',len(schools),'universities')
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        results=list(pool.map(check,pages))
    changes=old.get('recentChanges',[])
    discovered=old.get('recentDiscovered',[])
    status=[]
    for result in results:
        url=result['url']; previous=old_pages.get(url)
        err=result.get('error')
        if err:
            status.append({'schoolId':result['schoolId'],'url':url,'ok':False,'error':err})
            # Preserve old baseline on temporary network failures.
            continue
        status.append({'schoolId':result['schoolId'],'url':url,'ok':True,'title':result['title']})
        if previous and previous.get('hash') != result['hash']:
            changes.insert(0,{'schoolId':result['schoolId'],'schoolName':result['schoolName'],
                              'url':url,'title':result['title'],'detectedAt':NOW,'status':'unverified'})
        seen=set(previous.get('links',[])) if previous else set(result['links'])
        for link,label in result['links'].items():
            if link not in seen:
                discovered.insert(0,{'schoolId':result['schoolId'],'schoolName':result['schoolName'],
                                     'url':link,'title':label,'detectedAt':NOW,'status':'unverified'})
        old_pages[url]={'hash':result['hash'],'title':result['title'],'links':list(result['links']), 'checkedAt':NOW}
    def dedup_recent(items,field):
        picked=[];seen=set();cutoff=dt.datetime.now(dt.timezone.utc)-dt.timedelta(days=45)
        for row in items:
            try:
                when=dt.datetime.fromisoformat(row['detectedAt'].replace('Z','+00:00'))
                if when<cutoff:continue
            except (KeyError,ValueError):continue
            key=(row.get('schoolId'),row.get(field))
            if key in seen:continue
            seen.add(key);picked.append(row)
            if len(picked)>=50:break
        return picked
    changes=dedup_recent(changes,'url')
    discovered=dedup_recent(discovered,'url')
    state={'pages':old_pages,'recentChanges':changes,'recentDiscovered':discovered}
    STATE_FILE.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
    summary={'ok':sum(row['ok'] for row in status),'failed':sum(not row['ok'] for row in status)}
    output={'generatedAt':NOW,'summary':summary,'changes':changes,'discovered':discovered,'pages':status}
    OUT_FILE.parent.mkdir(parents=True,exist_ok=True)
    OUT_FILE.write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Completed:',summary,'changes:',len(changes),'new linked notices:',len(discovered))
    for row in status:
        if not row['ok']:print('NOT READABLE:',row['schoolId'],row['url'],row['error'])
    return 0

if __name__=='__main__': sys.exit(main())
