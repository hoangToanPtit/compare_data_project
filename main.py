import time
from flask import Flask, request, render_template, render_template_string, send_file
import pandas as pd
import os

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'upload'

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        merge_column = request.form.get('merge_column')
        merge_columns = [col.strip() for col in merge_column.split(',') if col.strip()]
        merge_type = request.form.get('merge_type')
        dfs = []
        i = 1
        while True:
            file = request.files.get('file' + str(i))
            if file is None:
                break
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(file_path)
            df = pd.read_csv(file_path)

            dfs.append((df, file.filename))
            
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

        result_file_name = f'result_{time.time()}.csv'
        merged_df.to_csv(result_file_name, index=False)

        return render_template('results.html', dfs=dfs, merged_df=merged_df, result_file=result_file_name)

    return render_template('upload.html')

@app.route('/download/<filename>')
def download_file(filename):
    return send_file(filename, as_attachment=True)

if __name__ == "__main__":
    app.run(port=5000, debug=True)
