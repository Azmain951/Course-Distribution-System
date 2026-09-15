"""
Course Requirements Generator
Dept. of CSE, Varendra University

Reads:
  - Batch_Registry.xlsx   (Batches, Section Overrides tabs; Batches tab must have
                            formulas already recalculated — open/save in Excel or
                            LibreOffice once, or pass a recalculated copy)
  - Curriculum_Courses.xlsx (Curriculum Courses, Elective Selection tabs)

Produces:
  - course_requirements.csv — one row per (course, section) slot, same shape the
    assignment engine already expects: course_code, course_title, semester,
    section, theory, lab, credit
  - special_load.csv — Thesis/Industrial Attachment/Technical Report Writing rows,
    kept separate since they aren't assigned like a normal theory/lab section

Logic:
  1. Pull every Active batch from Batch Registry (Status column already computed
     by that workbook's formulas).
  2. For each Active batch, look up its curriculum's course list at its current
     Current Semester Position in Curriculum Courses.
  3. Resolve any elective slot for that (curriculum, semester position) via
     Elective Selection — only if a course code has actually been entered there.
  4. Expand each course into one row per section. Default = every section listed
     in Section Overrides for that (batch, course); if no override row exists,
     default = ALL of the batch's sections (A, B, C... up to its Sections count).
  5. "Special" category courses (Project/Thesis, Industrial Attachment, Technical
     Report Writing) are pulled out into their own file instead of being expanded
     into theory/lab section slots.
"""
import pandas as pd
import openpyxl
import string


def section_letters(n):
    return list(string.ascii_uppercase[:n])


def load_batches(batch_registry_path):
    wb = openpyxl.load_workbook(batch_registry_path, data_only=True)
    ws = wb['Batches']
    rows = []
    for r in range(2, ws.max_row + 1):
        batch_no = ws.cell(row=r, column=1).value
        curriculum = ws.cell(row=r, column=2).value
        sections = ws.cell(row=r, column=5).value
        position = ws.cell(row=r, column=6).value
        status = ws.cell(row=r, column=7).value
        if batch_no is None or curriculum is None:
            continue
        if status != 'Active':
            continue
        rows.append(dict(batch_no=int(batch_no), curriculum=curriculum,
                          sections=int(sections), position=int(position)))
    return pd.DataFrame(rows, columns=['batch_no', 'curriculum', 'sections', 'position'])


def load_section_overrides(batch_registry_path):
    wb = openpyxl.load_workbook(batch_registry_path, data_only=True)
    ws = wb['Section Overrides']
    rows = []
    for r in range(2, ws.max_row + 1):
        batch_no = ws.cell(row=r, column=1).value
        code = ws.cell(row=r, column=2).value
        sections = ws.cell(row=r, column=3).value
        if batch_no is None or code is None or sections is None:
            continue
        if 'EXAMPLE' in str(ws.cell(row=r, column=4).value or ''):
            continue  # skip the illustrative example row
        letters = [s.strip() for s in str(sections).split(',') if s.strip()]
        rows.append(dict(batch_no=int(batch_no), course_code=str(code).strip(), sections=letters))
    return pd.DataFrame(rows, columns=['batch_no', 'course_code', 'sections'])


def load_curriculum_courses(curriculum_courses_path):
    return pd.read_excel(curriculum_courses_path, sheet_name='Curriculum Courses')


def load_elective_selection(curriculum_courses_path):
    wb = openpyxl.load_workbook(curriculum_courses_path, data_only=True)
    ws = wb['Elective Selection']
    rows = []
    for r in range(2, ws.max_row + 1):
        curriculum = ws.cell(row=r, column=1).value
        position = ws.cell(row=r, column=2).value
        group = ws.cell(row=r, column=3).value
        code = ws.cell(row=r, column=5).value
        title = ws.cell(row=r, column=6).value
        if curriculum is None or code is None:
            continue
        rows.append(dict(curriculum=curriculum, position=int(position), group=group,
                          course_code=str(code).strip(), course_title=title))
    return pd.DataFrame(rows, columns=['curriculum', 'position', 'group', 'course_code', 'course_title'])


def load_elective_pool_credits(curriculum_courses_path):
    df = pd.read_excel(curriculum_courses_path, sheet_name='Elective Pools')
    return df.set_index(['Curriculum', 'Semester Position', 'Course Code (Theory)'])[['Theory Credit', 'Lab Credit']]


def generate(batch_registry_path, curriculum_courses_path):
    batches = load_batches(batch_registry_path)
    overrides = load_section_overrides(batch_registry_path)
    curriculum_courses = load_curriculum_courses(curriculum_courses_path)
    elective_selection = load_elective_selection(curriculum_courses_path)
    elective_credits = load_elective_pool_credits(curriculum_courses_path)

    if batches.empty:
        return pd.DataFrame(), pd.DataFrame(), ["No Active batches found in Batch Registry."]

    warnings = []
    req_rows = []
    special_rows = []

    for _, b in batches.iterrows():
        curr, pos, batch_no, n_sections = b['curriculum'], b['position'], b['batch_no'], b['sections']

        courses = curriculum_courses[
            (curriculum_courses['Curriculum'] == curr) & (curriculum_courses['Semester Position'] == pos)
        ]
        if courses.empty:
            warnings.append(f"Batch {batch_no}: no course list found for {curr}, semester {pos}. Skipped.")
            continue

        course_list = []  # (code, title, credit, type, category)
        for _, c in courses.iterrows():
            course_list.append((c['Course Code'], c['Course Title'], c['Credit'], c['Type'], c['Category']))

        # resolve electives for this (curriculum, position), if any selections were made
        sel = elective_selection[(elective_selection['curriculum'] == curr) & (elective_selection['position'] == pos)]
        for _, e in sel.iterrows():
            code, title = e['course_code'], e['course_title']
            try:
                theory_credit, lab_credit = elective_credits.loc[(curr, pos, code)]
            except KeyError:
                warnings.append(f"Batch {batch_no}: elective '{code}' not found in Elective Pools for {curr} sem {pos}. Skipped.")
                continue
            course_list.append((code, title, theory_credit, 'Theory', 'Core'))
            lab_code = code[:-4] + f"{int(code[-4:]) + 1:04d}" if code[-4:].isdigit() else None
            if lab_code:
                course_list.append((lab_code, title + ' Lab', lab_credit, 'Lab', 'Core'))

        for code, title, credit, ctype, category in course_list:
            if category == 'Special':
                special_rows.append(dict(batch_no=batch_no, course_code=code, course_title=title,
                                          semester_position=pos, credit=credit, curriculum=curr))
                continue

            ov = overrides[(overrides['batch_no'] == batch_no) & (overrides['course_code'] == code)]
            sections = ov.iloc[0]['sections'] if not ov.empty else section_letters(n_sections)

            for sec in sections:
                req_rows.append(dict(
                    course_code=code, course_title=title, semester=f"{pos}{_ordinal_suffix(pos)}",
                    section=f"{batch_no}-{sec}", theory=(credit if ctype == 'Theory' else None),
                    lab=(credit if ctype == 'Lab' else None), credit=credit, batch_no=batch_no,
                ))

    req_df = pd.DataFrame(req_rows)
    special_df = pd.DataFrame(special_rows)
    return req_df, special_df, warnings


def _ordinal_suffix(n):
    return {1: 'st', 2: 'nd', 3: 'rd'}.get(n if n < 20 else n % 10, 'th')


if __name__ == '__main__':
    import sys
    batch_path = sys.argv[1] if len(sys.argv) > 1 else '../templates/Batch_Registry_TEMPLATE.xlsx'
    curriculum_path = sys.argv[2] if len(sys.argv) > 2 else '../templates/Curriculum_Courses.xlsx'
    req_df, special_df, warnings = generate(batch_path, curriculum_path)
    req_df.to_csv('generated_course_requirements.csv', index=False)
    special_df.to_csv('generated_special_load.csv', index=False)
    print(f"Generated {len(req_df)} course-section slots, {len(special_df)} special-load rows.")
    for w in warnings:
        print("WARNING:", w)
