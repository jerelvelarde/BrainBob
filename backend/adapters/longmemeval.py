"""LongMemEval_S adapter: one memory space per question; no evaluator (would leak). Official judge prompts."""
import collections, json, os, random, re
from brainbob import llm
from brainbob.types import Episode, Task

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "longmemeval_s_cleaned.json")


def anscheck_prompt(task, question, answer, response, abstention=False):
    if not abstention:
        if task in ['single-session-user', 'single-session-assistant', 'multi-session']:
            t = "I will give you a question, a correct answer, and a response from a model. Please answer yes if the response contains the correct answer. Otherwise, answer no. If the response is equivalent to the correct answer or contains all the intermediate steps to get the correct answer, you should also answer yes. If the response only contains a subset of the information required by the answer, answer no. \n\nQuestion: {}\n\nCorrect Answer: {}\n\nModel Response: {}\n\nIs the model response correct? Answer yes or no only."
        elif task == 'temporal-reasoning':
            t = "I will give you a question, a correct answer, and a response from a model. Please answer yes if the response contains the correct answer. Otherwise, answer no. If the response is equivalent to the correct answer or contains all the intermediate steps to get the correct answer, you should also answer yes. If the response only contains a subset of the information required by the answer, answer no. In addition, do not penalize off-by-one errors for the number of days. If the question asks for the number of days/weeks/months, etc., and the model makes off-by-one errors (e.g., predicting 19 days when the answer is 18), the model's response is still correct. \n\nQuestion: {}\n\nCorrect Answer: {}\n\nModel Response: {}\n\nIs the model response correct? Answer yes or no only."
        elif task == 'knowledge-update':
            t = "I will give you a question, a correct answer, and a response from a model. Please answer yes if the response contains the correct answer. Otherwise, answer no. If the response contains some previous information along with an updated answer, the response should be considered as correct as long as the updated answer is the required answer.\n\nQuestion: {}\n\nCorrect Answer: {}\n\nModel Response: {}\n\nIs the model response correct? Answer yes or no only."
        elif task == 'single-session-preference':
            t = "I will give you a question, a rubric for desired personalized response, and a response from a model. Please answer yes if the response satisfies the desired response. Otherwise, answer no. The model does not need to reflect all the points in the rubric. The response is correct as long as it recalls and utilizes the user's personal information correctly.\n\nQuestion: {}\n\nRubric: {}\n\nModel Response: {}\n\nIs the model response correct? Answer yes or no only."
        else:
            raise NotImplementedError
    else:
        t = "I will give you an unanswerable question, an explanation, and a response from a model. Please answer yes if the model correctly identifies the question as unanswerable. The model could say that the information is incomplete, or some other information is given but the asked information is not.\n\nQuestion: {}\n\nExplanation: {}\n\nModel Response: {}\n\nDoes the model correctly identify the question as unanswerable? Answer yes or no only."
    return t.format(question, answer, response)


def judge(q, hyp):
    p = anscheck_prompt(q["question_type"], q["question"], q["answer"], hyp, q["question_id"].endswith("_abs"))
    cl = llm.complete("judge", [{"role": "user", "content": p}], max_tokens=1024).strip().lower()
    return cl.startswith("yes") or (bool(re.search(r"\byes\b", cl)) and not re.search(r"\bno\b", cl))


def subset(n):
    """The fixed 50-question stratified subset (subset_ids.json), n sampled from it."""
    data = json.load(open(DATA, encoding="utf-8"))
    ids = json.load(open(os.path.join(ROOT, "subset_ids.json")))["ids"]
    byid = {d["question_id"]: d for d in data}
    qs = [byid[i] for i in ids]
    if n < len(qs):
        rng = random.Random(1); qs = qs[:]; rng.shuffle(qs); qs = qs[:n]
    return qs


def sessions(q):
    return sorted(zip(q["haystack_dates"], q["haystack_session_ids"], q["haystack_sessions"]), key=lambda x: x[0])


def episodes(q):
    return [Episode(sid, "\n".join(f"{m['role']}: {m['content']}" for m in s), d, sid) for d, sid, s in sessions(q)]


def task(q):
    """Gold stays inside grade()."""
    return Task(q["question_id"], q["question"], lambda a: judge(q, a), now=q["question_date"])
