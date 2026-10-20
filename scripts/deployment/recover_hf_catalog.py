"""Rebuild a private recovery catalog from pinned remote manifests after host loss."""
import argparse
from datetime import datetime
import importlib.util
import json
import os
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[2]

def collect(archive,hub):
    info=hub.api.repo_info(archive.REPO,repo_type='dataset')
    if info.private is not True:raise RuntimeError('PRIVATE_REPOSITORY_REQUIRED')
    if not re.fullmatch('[a-f0-9]{40}',info.sha):raise RuntimeError('PINNED_CATALOG_REVISION_REQUIRED')
    versions=[];latest={}
    for item in sorted(info.siblings,key=lambda x:x.rfilename):
        name=item.rfilename
        if not re.fullmatch(r'manifests/[a-f0-9]{64}/[a-f0-9]{64}\.json',name):continue
        value=json.loads(hub.download_memory(name,info.sha))
        if value.get('repo')!=archive.REPO:raise RuntimeError('WRONG_REPOSITORY')
        archive.safe_remote_path(value.get('object'),value.get('object_revision'))
        stamp=datetime.fromisoformat(value['archived_utc'])
        if stamp.tzinfo is None:raise RuntimeError('ARCHIVE_CLOCK_REQUIRED')
        identity=value.get('logical_source') or 'legacy:'+value['source']
        record=dict(identity=identity,remote_manifest=name,manifest=value,
                    legacy_mapping_required='logical_source' not in value)
        versions.append(record)
        if identity not in latest or stamp>datetime.fromisoformat(latest[identity]['manifest']['archived_utc']):
            latest[identity]=record
    return dict(schema_version=1,repo=archive.REPO,catalog_revision=info.sha,
                versions=versions,latest=latest,contains_credentials=False,live_authorized=False)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',required=True)
    p.add_argument('--output');p.add_argument('--logical-source');p.add_argument('--manifest-output')
    a=p.parse_args();config=json.loads(Path(a.config).read_text(encoding='utf-8-sig'))
    spec=importlib.util.spec_from_file_location('hf_archive',ROOT/'scripts/ai/hf_archive_sync.py')
    archive=importlib.util.module_from_spec(spec);spec.loader.exec_module(archive)
    archive.configure_runtime(config)
    client=config.get('client_dir') or os.environ.get('KATARINA_HF_CLIENT_DIR')
    if client:sys.path.insert(0,client)
    import certifi
    os.environ['SSL_CERT_FILE']=certifi.where();os.environ['HF_HUB_DISABLE_XET']='1'
    hub=archive.Hub(archive.load_token(config))
    catalog=collect(archive,hub)
    output=Path(a.output) if a.output else archive.BASE/'recovery-catalog.private.json'
    archive.atomic_json(output,catalog)
    if a.logical_source:
        if not a.manifest_output:raise RuntimeError('MANIFEST_OUTPUT_REQUIRED')
        record=catalog['latest'].get(a.logical_source)
        if not record:raise RuntimeError('LOGICAL_SOURCE_NOT_FOUND')
        archive.atomic_json(a.manifest_output,record['manifest'])
    print(json.dumps(dict(status='CATALOG_SAVED',revision=catalog['catalog_revision'],
                         versions=len(catalog['versions']),identities=len(catalog['latest']),live_authorized=False)))

if __name__=='__main__':
    try:main()
    except Exception as error:
        print(json.dumps(dict(status='CATALOG_FAILED',error=type(error).__name__)))
        raise SystemExit(1) from None
