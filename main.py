import time
from flask import Flask, request, render_template, render_template_string, send_file
import pandas as pd
import os
import re

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'upload'

def split_expression(expr):
    operators = ['+', '-', '*', '/']
    expr_parts = expr.split()
    columns = []
    ops = []
    for part in expr_parts:
        if part in operators:
            ops.append(part)
        else:
            columns.append(part)
    return columns, ops

def calculate_expression(row, columns, ops):
    result = float(row[columns[0]]) if is_convertable_to_float(row[columns[0]]) else 0
    for i, op in enumerate(ops):
        val = float(row[columns[i + 1]]) if is_convertable_to_float(row[columns[i + 1]]) else 0
        if op == '+':
            result += val
        elif op == '-':
            result -= val
        elif op == '*':
            result *= val
        elif op == '/':
            if val != 0:
                result /= val
    return result

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        merge_column = request.form.get('merge_column')
        merge_columns = [col.strip() for col in merge_column.split(',') if col.strip()]
        merge_type = request.form.get('merge_type')
        compare_formula = request.form.get('compare_formula')
        dfs = []
        dfs_limited = []
        i = 1
        while True:
            file = request.files.get('file' + str(i))
            if file is None:
                break
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(file_path)
            df = pd.read_csv(file_path)
            limited_df = df.head(5)  # Giới hạn số dòng tối đa của DataFrame
            limited_df.insert(0, '#', range(1, 1 + len(limited_df)))  # Thêm cột số thứ tự
            limited_html = limited_df.to_html(index=False) + '...'

            dfs.append((df, file.filename))
            dfs_limited.append((limited_df, limited_html, file.filename))  # Lưu các DataFrame đã giới hạn và HTML
            
            os.remove(file_path)
            
            df.columns = df.columns.str.strip()
            i += 1

        for column in merge_columns:
            for df, filename in dfs:
                if column not in df.columns:
                    return render_template_string('<p>Error: Column "{}" not found in all files.</p>'.format(column))

        merged_df = dfs[0][0]
        for df, filename in dfs[1:]:
            merged_df = merged_df.merge(df, on=merge_columns, how=merge_type)
        merged_df = merged_df.fillna('')
        merged_df.insert(0, '#', range(1, 1 + len(merged_df)))  # Thêm cột số thứ tự

        if compare_formula:
            parts = compare_formula.split("=")
            if len(parts) == 2:
                left_expr, right_expr = parts
                left_expr = left_expr.strip()
                right_expr = right_expr.strip()

                left_columns, left_ops = split_expression(left_expr)
                right_columns, right_ops = split_expression(right_expr)
                merged_df["compare_result"] = merged_df.apply(lambda row: "X" if any(str(row[col]).strip() == '' for col in left_columns + right_columns) else "", axis=1)

                merged_df[left_expr] = merged_df.apply(lambda row: calculate_expression(row, left_columns, left_ops), axis=1)
                merged_df[right_expr] = merged_df.apply(lambda row: calculate_expression(row, right_columns, right_ops), axis=1)
                merged_df["compare_result"] = merged_df.apply(lambda row: "X" if row[left_expr] != row[right_expr] else "", axis=1)

                cols = list(merged_df.columns)
                cols.remove('compare_result')
                merged_df = merged_df[cols + ['compare_result']]

        result_file_name = f'result_{time.time()}.csv'
        merged_df.to_csv(result_file_name, index=False)

        return render_template('results.html', dfs=dfs_limited, merged_df=merged_df, result_file=result_file_name)

    return render_template('upload.html')

@app.route('/download/<filename>')
def download_file(filename):
    return send_file(filename, as_attachment=True)

def is_convertable_to_float(value):
    try:
        float(value)
        return True
    except ValueError:
        return False

if __name__ == "__main__":
    app.run(port=5000, debug=True)
