from number_app.storage.files import check_snapshot

def healthy_row(catalog,batch_id):
    row=catalog.get(batch_id)
    if not row or row['status']!='COMPLETED': raise ValueError('该批次尚未通过完整审查或已损坏')
    try: check_snapshot(row['batch_dir'],row['manifest_sha256'],row['request_sha256'])
    except Exception as e:
        catalog.update(batch_id,status='DAMAGED',message=str(e)); raise ValueError('批次已损坏，停止查看和导出：'+str(e))
    return row
