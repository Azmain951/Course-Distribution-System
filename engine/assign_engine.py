"""
Teacher-Course Assignment Engine v2
Dept. of CSE, Varendra University

Rules (as specified by department):
1. Only choice-driven CSE courses are auto-assigned. Math/Physics/EEE/External
   service courses are pre-locked (fed in separately, not derived from choices).
2. Each teacher has:
     - a credit_limit (by designation: Lecturer 18, Asst.Prof 15, Assoc.Prof 12,
       Coordinator 9, Head 6 -- overridable per individual for waivers)
     - a theory_target = max number of THEORY courses/sections they take
       (default by designation, overridable per individual)
3. Priority order = SL No (already encodes designation seniority).
4. PHASE 1 - Theory pass: each teacher is offered choices in rank order; only
   choices that are THEORY courses count toward their theory_target. Assign
   sections of that course (in section order) until theory_target or
   credit_limit is hit, then move to next choice.
5. PHASE 2 - Mandatory pairing: whenever a teacher is assigned Theory-Section-S
   of a course, they are AUTOMATICALLY placed as one of the two teachers on
   the corresponding LAB-Section-S of that same course (sibling course code),
   if a lab exists and there's room, credit allowing. This is forced,
   independent of the teacher's lab preference.
6. PHASE 3 - Lab partner pass: remaining open lab seats (the "second teacher")
   are filled from LAB choices in rank order, same priority-by-SL-No sweep,
   preferring to complete already one-filled pairs first.
7. Whatever is left after that is reported for manual assignment.
"""
import pandas as pd
import re
from collections import defaultdict

DEFAULT_CREDIT_LIMIT = {
    'Head': 6, 'Coordinator': 9, 'Associate Professor': 12,
    'Assistant Professor': 15, 'Lecturer': 18, 'Professor': 12,
}
DEFAULT_THEORY_TARGET = {
    'Head': 1, 'Coordinator': 2, 'Associate Professor': 2,
    'Assistant Professor': 3, 'Lecturer': 3, 'Professor': 2,
}

def norm_title(s):
    return re.sub(r'\s+', ' ', str(s).strip().lower())

def sibling_lab_code(course_code):
    """CSE 2103 -> CSE 2104 (theory code + 1). Returns None if pattern doesn't apply."""
    m = re.match(r'^([A-Za-z]+)\s*(\d+)$', str(course_code).strip())
    if not m:
        return None
    prefix, num = m.groups()
    return f"{prefix} {int(num)+1:04d}" if len(num) == 4 else f"{prefix} {int(num)+1}"


def build_slots(req):
    slots = []
    for i, r in req.iterrows():
        is_lab = pd.notna(r['lab'])
        needed = 2 if is_lab else 1
        slots.append({
            'slot_id': i, 'course_code': str(r['course_code']).strip(),
            'course_title': r['course_title'], 'norm_title': norm_title(r['course_title']),
            'semester': r['semester'], 'section': r['section'], 'is_lab': is_lab,
            'credit': r['credit'], 'needed': needed, 'assigned': [], 'forced': [],
        })
    return slots


def build_teacher_config(choices_df, teacher_master_df, config_overrides=None):
    """Merge choices with master; fill credit_limit / theory_target from designation
    defaults unless an override is supplied."""
    t = choices_df.merge(
        teacher_master_df[['name', 'initial', 'credit_limit']],
        left_on='name_matched' if 'name_matched' in choices_df.columns else 'name',
        right_on='name', how='left', suffixes=('', '_m'))
    t['initial'] = t['initial'].fillna(
        t['name'].apply(lambda n: ''.join(w[0] for w in str(n).replace('.', '').split()[:3]).upper()))
    t['credit_limit'] = t.apply(
        lambda row: row['credit_limit'] if pd.notna(row['credit_limit'])
        else DEFAULT_CREDIT_LIMIT.get(row['designation'], 18), axis=1)
    t['theory_target'] = t['designation'].map(DEFAULT_THEORY_TARGET).fillna(3)
    if config_overrides:
        for name, vals in config_overrides.items():
            mask = t['name'] == name
            for k, v in vals.items():
                t.loc[mask, k] = v
    return t.sort_values('sl_no').reset_index(drop=True)


def title_lookup(slots):
    """norm_title -> is_lab (assumes consistent per title)."""
    d = {}
    for s in slots:
        d[s['norm_title']] = s['is_lab']
    return d


def run_assignment(slots, teachers_df):
    assigned_credit = defaultdict(float)
    theory_count = defaultdict(int)
    log = []
    slot_by_code_section = {(s['course_code'], str(s['section'])): s for s in slots}
    ttl = title_lookup(slots)

    # ---- PHASE 1: theory pass ----
    for _, trow in teachers_df.iterrows():
        init, limit, target = trow['initial'], trow['credit_limit'], trow['theory_target']
        for rank in range(1, 7):
            title = trow.get(f'choice{rank}')
            if pd.isna(title):
                continue
            nt = norm_title(title)
            if ttl.get(nt, True):  # unknown or lab -> skip in theory pass
                continue
            if theory_count[init] >= target:
                continue
            candidates = [s for s in slots if s['norm_title'] == nt
                          and len(s['assigned']) < s['needed'] and init not in s['assigned']]
            candidates.sort(key=lambda s: str(s['section']))
            for s in candidates:
                if theory_count[init] >= target:
                    break
                add = s['credit']
                if assigned_credit[init] + add > limit + 1e-6:
                    continue
                s['assigned'].append(init)
                assigned_credit[init] += add
                theory_count[init] += 1
                log.append(dict(phase='theory', initial=init, name=trow['name'],
                                 course_code=s['course_code'], course_title=s['course_title'],
                                 semester=s['semester'], section=s['section'],
                                 choice_rank=rank, credit_given=add))
                # ---- PHASE 2: mandatory lab pairing, done inline right after theory assign ----
                lab_code = sibling_lab_code(s['course_code'])
                lab_slot = slot_by_code_section.get((lab_code, str(s['section'])))
                if lab_slot and init not in lab_slot['assigned'] and len(lab_slot['assigned']) < lab_slot['needed']:
                    add_lab = lab_slot['credit'] / lab_slot['needed']
                    if assigned_credit[init] + add_lab <= limit + 1e-6:
                        lab_slot['assigned'].append(init)
                        lab_slot['forced'].append(init)
                        assigned_credit[init] += add_lab
                        log.append(dict(phase='mandatory_lab', initial=init, name=trow['name'],
                                         course_code=lab_slot['course_code'], course_title=lab_slot['course_title'],
                                         semester=lab_slot['semester'], section=lab_slot['section'],
                                         choice_rank=rank, credit_given=add_lab))

    # ---- PHASE 3: lab partner pass (preference driven) ----
    for _, trow in teachers_df.iterrows():
        init, limit = trow['initial'], trow['credit_limit']
        for rank in range(1, 7):
            title = trow.get(f'choice{rank}')
            if pd.isna(title):
                continue
            nt = norm_title(title)
            if not ttl.get(nt, False):  # only labs here
                continue
            candidates = [s for s in slots if s['norm_title'] == nt
                          and len(s['assigned']) < s['needed'] and init not in s['assigned']]
            candidates.sort(key=lambda s: (0 if s['assigned'] else 1, str(s['section'])))
            for s in candidates:
                add = s['credit'] / s['needed']
                if assigned_credit[init] + add > limit + 1e-6:
                    continue
                s['assigned'].append(init)
                assigned_credit[init] += add
                log.append(dict(phase='lab_pref', initial=init, name=trow['name'],
                                 course_code=s['course_code'], course_title=s['course_title'],
                                 semester=s['semester'], section=s['section'],
                                 choice_rank=rank, credit_given=add))

    return slots, assigned_credit, theory_count, pd.DataFrame(log)


def unassigned_report(slots):
    rows = []
    for s in slots:
        missing = s['needed'] - len(s['assigned'])
        if missing > 0:
            rows.append(dict(course_code=s['course_code'], course_title=s['course_title'],
                              semester=s['semester'], section=s['section'], is_lab=s['is_lab'],
                              seats_missing=missing,
                              already_assigned=', '.join(s['assigned']) if s['assigned'] else ''))
    return pd.DataFrame(rows)
