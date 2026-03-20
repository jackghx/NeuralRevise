import time
import re
import json
import os
import traceback
import requests
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# ── CONFIG ───────────────────────────────────────────────────────────────────
COURSE_ID    = "90" # Change to your course ID if needed
OLLAMA_URL   = "http://localhost:11434/api/generate"  # Change to your Ollama IP if localhost is not working
OLLAMA_MODEL = "llama3.1:8b" # Change model if needed
QUIZ_TARGET  = 50
TERMS_TARGET = 20
DELAY        = 0.8
LEARNED_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "learned.json")
# ─────────────────────────────────────────────────────────────────────────────

QUIZ_URL  = "https://smartrevise.online/student/revise/Question/" + COURSE_ID
TERMS_URL = "https://smartrevise.online/student/reviseterminology/index/" + COURSE_ID

def load_learned():
    if os.path.exists(LEARNED_FILE):
        try:
            with open(LEARNED_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print("[Warning] Could not load learned.json:", e)
    return {}

def save_learned(data):
    tmp = LEARNED_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, LEARNED_FILE)

def get_correct_answer(page):
    try:
        correct = page.locator("a.js_answerButton.btn-success div.col").first
        correct.wait_for(state="visible", timeout=3000)
        return correct.inner_text().strip()
    except:
        return None

def ask_ai(prompt):
    try:
        r = requests.post(OLLAMA_URL, json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 60, "num_ctx": 512} # Increase for a larger context window
        }, timeout=60)
        return r.json().get("response", "").strip()
    except Exception as e:
        print("[Ollama error]", e)
        return ""

def quiz_prompt(question, options):
    opts = "\n".join(f"{i+1}. {o}" for i, o in enumerate(options))
    return "A Level CS. Answer only with the exact option text.\nQ: " + question + "\n" + opts

def terms_prompt(term):
    return "Define this OCR A Level Computer Science term in one short sentence only: " + term

def click_answer(els, options, answer):
    num_match = re.match(r'^(\d+)[.):\s]', answer.strip())
    if num_match:
        idx = int(num_match.group(1)) - 1
        if 0 <= idx < len(els):
            els[idx].click()
            print("Clicked by index:", options[idx])
            return
    for i, opt in enumerate(options):
        if answer.lower().strip() == opt.lower().strip():
            els[i].click()
            print("Clicked:", opt)
            return
    for i, opt in enumerate(options):
        if answer.lower().strip() in opt.lower() or opt.lower() in answer.lower().strip():
            els[i].click()
            print("Clicked:", opt)
            return
    els[0].click()
    print("No match, clicked first option:", options[0])

def run_quiz(page):
    print("Starting Quiz")
    page.goto(QUIZ_URL)
    page.wait_for_load_state("networkidle")
    time.sleep(DELAY)
    learned = load_learned()
    print(f"Loaded {len(learned)} learned answers")
    answered = 0
    while answered < QUIZ_TARGET:
        try:
            page.wait_for_selector("#questiontext", timeout=10000)
            question = page.locator("#questiontext").inner_text().strip()
            answer_links = page.locator("a.js_answerButton").all()
            options = []
            els = []
            for a in answer_links:
                txt = a.locator("div.col").inner_text().strip()
                if txt and "don't know" not in txt.lower():
                    options.append(txt)
                    els.append(a)
            if not options:
                print("No options found, stopping")
                break
            print(f"\nQ{answered+1}: {question}")
            print("Options:", options)
            if question in learned:
                answer = learned[question]
                print("From memory:", answer)
                time.sleep(2)
            else:
                answer = ask_ai(quiz_prompt(question, options))
                print("AI:", answer)
            click_answer(els, options, answer)
            time.sleep(DELAY)
            correct = get_correct_answer(page)
            if correct:
                if correct != learned.get(question):
                    learned[question] = correct
                    save_learned(learned)
                if correct != answer:
                    print("Correct was:", correct, "(learned for next time)")
                else:
                    print("Correct!")
            try:
                next_btn = page.locator("#lnkNext")
                next_btn.wait_for(state="visible", timeout=5000)
                next_btn.click()
                time.sleep(DELAY)
            except PlaywrightTimeout:
                print("Next button not found, reloading")
                page.reload()
                time.sleep(DELAY)
            answered += 1
            page.wait_for_load_state("networkidle")
        except Exception as e:
            print("Quiz error:", e)
            traceback.print_exc()
            page.screenshot(path="quiz_error.png")
            break
    print(f"Quiz done: {answered} questions, {len(learned)} answers in memory")

def run_terms(page):
    print("Starting Terms")
    page.goto(TERMS_URL)
    page.wait_for_load_state("networkidle")
    time.sleep(3)
    assessed = 0
    while assessed < TERMS_TARGET:
        try:
            page.wait_for_selector(".carousel-item.active span.term", timeout=10000)
            term = page.locator(".carousel-item.active span.term").first.inner_text().strip()
            if not term or term == "Loading cards...":
                print("No term loaded, stopping")
                break
            print(f"\nCard {assessed+1}: {term}")
            definition = ask_ai(terms_prompt(term))
            print("Definition:", definition[:80])
            page.locator("#activeAnswer").click()
            page.locator("#activeAnswer").fill("")
            page.locator("#activeAnswer").press_sequentially(definition[:400], delay=20)
            time.sleep(DELAY)
            page.locator("#btnFlip").click()
            time.sleep(DELAY)
            conf_btns = page.locator(".js_btnConfidence").all()
            if len(conf_btns) >= 2:
                conf_btns[1].click()
                print("Clicked neutral confidence")
            else:
                print("Confidence buttons not found")
                page.screenshot(path="terms_confidence_error.png")
            time.sleep(DELAY)
            page.locator("#btnNext").click()
            time.sleep(DELAY)
            page.wait_for_load_state("networkidle")
            assessed += 1
        except Exception as e:
            print("Terms error:", e)
            traceback.print_exc()
            page.screenshot(path="terms_error.png")
            break
    print("Terms done:", assessed, "cards")

def main():
    with sync_playwright() as pw:
        print("Connecting to Chrome on port 9222...")
        browser = pw.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]
        pages = context.pages
        page = None
        for p in pages:
            if "smartrevise.online" in p.url:
                page = p
                break
        if not page:
            page = context.new_page()
        page.bring_to_front()
        print("Using tab:", page.url)
        try:
            print("Log into SmartRevise then press Enter...")
            input()
            run_quiz(page)
            run_terms(page)
        except Exception as e:
            print("FATAL:", e)
            traceback.print_exc()
            page.screenshot(path="fatal_error.png")
            input("Press Enter to close...")

if __name__ == "__main__":
    main()
