from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import teleos
import os

app = FastAPI()

HTML_PATH = os.path.join(os.path.dirname(__file__), "playground.html")

@app.get("/", response_class=HTMLResponse)
async def root():
    with open(HTML_PATH, encoding="utf-8") as f:
        return f.read()

@app.post("/run")
async def run_program(request: Request):
    body = await request.json()
    source: str = body.get("source", "")
    try:
        engine = teleos.loads(source)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)

    results = []

    try:
        from teleos.parser import parse_string, Query, Assert
        kb = parse_string(source)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)

    for item in kb.queries:
        q = item
        query_str = " ".join(q.terms)
        try:
            if q.kind == "ask":
                answer = engine.ask(query_str)
                results.append({"kind": "ask", "query": query_str, "answer": str(answer)})
            elif q.kind == "why":
                answer = engine.why(query_str)
                results.append({"kind": "why", "query": query_str, "answer": answer})
            elif q.kind == "all":
                answer = engine.all(query_str)
                results.append({"kind": "all", "query": query_str, "answer": answer})
        except Exception as e:
            results.append({"kind": q.kind, "query": query_str, "error": str(e)})

    test_results = []
    for a in kb.asserts:
        query_str = " ".join(a.terms)
        try:
            result = engine.ask(query_str)
            passed = (result == a.expect)
            test_results.append({
                "query": query_str,
                "expect": a.expect,
                "got": result,
                "passed": passed,
            })
        except Exception as e:
            test_results.append({
                "query": query_str,
                "expect": a.expect,
                "got": None,
                "passed": False,
                "error": str(e),
            })

    return JSONResponse({"results": results, "tests": test_results})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
