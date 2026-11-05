from __future__ import annotations
from pathlib import Path
from html import escape
import hashlib
import json
import shutil
import os
import http.client
from contextlib import contextmanager
from .config import load_config
from .validation import normalize_records,review_issues,now_kst,ALLOWED_RIGHTS
from .images import resize_product_image,download_image
from exporters.table_exporter import render_product_table

ISSUE_TEXT={"MODEL_REQUIRED":"모델번호 미입력","IMAGE_RIGHTS_NOT_CONFIRMED":"이미지 권한 미확인",
"IMAGE_MISSING":"상품 이미지 없음","PRICE_MISSING":"가격 미수집","URL_INVALID":"URL 미확인",
"MATCH_NOT_REVIEWED":"동일 모델·옵션 미확인","TERMS_NOT_REVIEWED":"배송비·조건 미확인",
"TIMESTAMP_REQUIRED":"가격 확인시각 필요","STALE_PRICE":"가격 확인시각 경과","FUTURE_TIMESTAMP":"미래 확인시각",
"INVALID_PRICE":"모호하거나 유효하지 않은 가격","CONDITION_REQUIRED":"비교 조건 설명 필요","IMAGE_CREDIT_REQUIRED":"이미지 출처·권한 근거 표기 필요"}

def explain(issue: str) -> str:
    source,_,key=issue.partition(":")
    if key:
        return {"danawa":"다나와","naver":"네이버"}.get(source,source)+": "+ISSUE_TEXT.get(key,key)
    return ISSUE_TEXT.get(issue,issue)

def atomic_json(path: Path,value: object):
    temp=path.with_suffix(path.suffix+".tmp")
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding="utf-8")
    temp.replace(path)

@contextmanager
def pipeline_lock(root: Path):
    folder=root/'07_DATA/state'
    folder.mkdir(parents=True,exist_ok=True)
    path=folder/'pipeline.lock'
    try:
        fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    except FileExistsError as e:
        raise ValueError("PIPELINE_BUSY: 다른 실행이 진행 중입니다. 강제 종료 후 남은 lock은 모든 실행 종료를 확인한 뒤 삭제하세요.") from e
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as stream:
            stream.write(json.dumps({'pid':os.getpid(),'started_at':now_kst().isoformat()}))
        yield
    finally:
        path.unlink(missing_ok=True)

def run_pipeline(root: Path,records: object,mode: str="MANUAL_IMPORT") -> dict:
    with pipeline_lock(root):
        return _run_pipeline(root,records,mode)

def _run_pipeline(root: Path,records: object,mode: str="MANUAL_IMPORT") -> dict:
    if mode not in {"DEMO","MANUAL_IMPORT"}:
        raise ValueError("지원 모드: DEMO / MANUAL_IMPORT")
    config=load_config(root)
    rows=normalize_records(records)
    now=now_kst()
    canonical=json.dumps({"rows":rows,"image":config["image"],"mode":mode},sort_keys=True,ensure_ascii=False)
    digest=hashlib.sha256(canonical.encode()).hexdigest()[:12]
    run_id=now.strftime("%Y%m%d")+"_"+mode.lower()+"_"+digest
    out=root/"08_OUTPUT/runs"/run_id
    reused=out.exists()
    out.mkdir(parents=True,exist_ok=True)
    (out/"images").mkdir(exist_ok=True)
    review=[]
    for i,row in enumerate(rows,1):
        (out/"images"/f"product_{i:02d}.jpg").unlink(missing_ok=True)
        issues=review_issues(row,config["quality"]["max_price_age_hours"],now)
        original=row.get("image_path","")
        row["original_image_path"]=original
        row["image_path"]=None
        if row.get("image_rights") in ALLOWED_RIGHTS:
            try:
                if not original and row.get("image_url"):
                    original=download_image(root,row["image_url"],config["image"],row["image_rights"],row.get("image_credit",""))
                    row["original_image_path"]=original
                if original:
                    image=resize_product_image(root,original,config["image"]["width_px"],config["image"]["height_px"],config["image"]["dpi"],config["image"]["max_pixels"])
                    row["image_path"]=image
                    shutil.copyfile(root/image,out/"images"/f"product_{i:02d}.jpg")
            except (ValueError,OSError,http.client.HTTPException) as e:
                issues.append("IMAGE_ERROR:"+str(e)[:160])
        if not row["image_path"]:
            issues.append("IMAGE_MISSING")
        review.append({"row":i,"query":row["query"],"issues":issues,"details":[explain(x) for x in issues]})
    gate="DEMO_ONLY" if mode=="DEMO" else ("HOLD" if any(x["issues"] for x in review) else "READY_FOR_MANUAL_REVIEW")
    title=("[테스트 데이터] " if mode=="DEMO" else "[사용자 입력값] ")+"상품 가격 비교표"
    html=render_product_table(rows,image_base_dir=root,title=title)
    disclaimer=("데모 가격·제품·링크입니다. 실제 시세와 관계없으며 게시할 수 없습니다." if mode=="DEMO" else
                "사용자가 확인·입력한 자료의 검토용 결과입니다. 실시간 수집·자동 사실검증·블로그 발행을 수행하지 않았습니다.")
    notes=f'<section class="note"><h2>검토 상태: {escape(gate)}</h2><p>{escape(disclaimer)}</p>'
    notes+='<p>표의 최저가는 입력된 비교 조건 범위의 값이며 전체 시장의 절대 최저가를 보장하지 않습니다. 가격의 원래 확인시각을 유지합니다.</p>'
    for row,item in zip(rows,review):
        notes+=f'<h3>{item["row"]}. {escape(row["query"])}</h3>'
        for source,label in (("danawa","다나와"),("naver","네이버")):
            notes+=f'<p>{label} 확인시각: {escape(row[source+"_observed_at"] or "미확인")} / 조건: {escape(row[source+"_condition"])}</p>'
        notes+=f'<p>이미지 권한(사용자 선언): {escape(row["image_rights"] or "미확인")} / 표기: {escape(row["image_credit"] or "미입력")}</p>'
        notes+='<p>'+escape(" · ".join(item["details"]) or "자동 형식 검사 통과 — 게시 전 사람이 출처와 내용을 다시 검토해야 합니다.")+"</p>"
    notes+='</section>'
    html=html.replace('<body>', '<body><section class="note"><strong>'+escape(gate)+'</strong> — '+escape(disclaimer)+'</section>')
    html=html.replace('</body>',notes+'</body>')
    (out/'product_table.html').write_text(html,encoding='utf-8')
    atomic_json(out/'normalized_products.json',rows)
    summary={"project_version":"1.0.0","run_id":run_id,"mode":mode,"review_gate":gate,"row_count":len(rows),
             "reviewed_at":now.isoformat(),"network_price_collection":False,"published":False,"reused_output":reused,
             "preview_url":"/output/"+run_id+"/product_table.html","output_relative":out.relative_to(root).as_posix(),"review":review}
    atomic_json(out/'run_report.json',summary)
    handoff=f"""# 네이버 블로그 수동 게시 준비\n\n상태: {gate}\n\n{disclaimer}\n\n1. product_table.html의 모델·옵션·가격 확인시각·배송비 조건을 검토합니다.\n2. images/ 파일의 사용 권한과 출처를 확인합니다.\n3. 네이버 블로그에서 직접 로그인하고 새 글을 작성합니다. 계정 비밀번호를 프로그램에 입력하지 않습니다.\n4. 본문은 별도 콘텐츠 브리프로 작성하고 이미지는 에디터로 업로드합니다. HTML의 base64 이미지는 게시 URL이 아닙니다.\n5. 에디터가 표 붙여넣기를 보존하는지 먼저 1개 행으로 시험합니다. 보존하지 않으면 에디터의 표 도구로 구성합니다.\n6. 모바일/PC 미리보기를 확인하고, 직접 공개 범위와 발행을 결정합니다.\n\n이 폴더는 업로드 준비 자료이며 네이버 서버의 임시저장 글이 아닙니다.\n실시간 가격 갱신과 자동 게시 어댑터는 구현되지 않았습니다.\n"""
    (out/'NAVER_HANDOFF.md').write_text(handoff,encoding='utf-8')
    atomic_json(root/'07_DATA/state/latest_run.json',summary)
    return summary
