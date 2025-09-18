
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
廣告管理工具 - ad_manager.py
用於管理廣告內容和目標設定
'''

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import mysql.connector
from datetime import datetime, date
import os
import shutil

class AdManagerTool:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("廣告管理系統")
        self.root.geometry("1000x700")

        # 資料庫連接
        self.db_connection = None
        self.connect_database()

        # 廣告目錄
        self.ad_images_dir = "advertisements/images"
        self.ad_videos_dir = "advertisements/videos"
        os.makedirs(self.ad_images_dir, exist_ok=True)
        os.makedirs(self.ad_videos_dir, exist_ok=True)

        self.setup_gui()
        self.load_advertisements()

    def connect_database(self):
        try:
            self.db_connection = mysql.connector.connect(
                host='localhost',
                user='pi',
                password='raspberry',
                database='face_ad_system'
            )
        except mysql.connector.Error as err:
            messagebox.showerror("資料庫錯誤", f"無法連接資料庫: {err}")

    def setup_gui(self):
        # 主要框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 廣告列表
        list_frame = ttk.LabelFrame(main_frame, text="廣告列表", padding="10")
        list_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0,10))

        # 樹狀檢視
        columns = ('ID', '標題', '目標分類', '性別', '年齡', '狀態')
        self.ad_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)

        for col in columns:
            self.ad_tree.heading(col, text=col)
            self.ad_tree.column(col, width=80)

        # 捲軸
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.ad_tree.yview)
        self.ad_tree.configure(yscrollcommand=scrollbar.set)

        self.ad_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # 按鈕
        button_frame = ttk.Frame(list_frame)
        button_frame.grid(row=1, column=0, columnspan=2, pady=10)

        ttk.Button(button_frame, text="新增廣告", command=self.add_advertisement).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="編輯", command=self.edit_advertisement).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="刪除", command=self.delete_advertisement).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="重新載入", command=self.load_advertisements).pack(side=tk.LEFT, padx=5)

        # 編輯區域
        edit_frame = ttk.LabelFrame(main_frame, text="廣告編輯", padding="10")
        edit_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 基本資訊
        ttk.Label(edit_frame, text="廣告標題:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.title_var = tk.StringVar()
        ttk.Entry(edit_frame, textvariable=self.title_var, width=40).grid(row=0, column=1, pady=2)

        ttk.Label(edit_frame, text="廣告內容:").grid(row=1, column=0, sticky=(tk.W, tk.N), pady=2)
        self.content_text = tk.Text(edit_frame, width=40, height=5)
        self.content_text.grid(row=1, column=1, pady=2)

        # 目標設定
        target_frame = ttk.LabelFrame(edit_frame, text="目標設定")
        target_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)

        ttk.Label(target_frame, text="產品分類:").grid(row=0, column=0, sticky=tk.W)
        self.category_var = tk.StringVar()
        category_combo = ttk.Combobox(target_frame, textvariable=self.category_var, width=15)
        category_combo['values'] = ('electronics', 'fashion', 'sports', 'beauty', 'food', 'appliances', 'books', 'general')
        category_combo.grid(row=0, column=1, padx=5)

        ttk.Label(target_frame, text="目標性別:").grid(row=0, column=2, sticky=tk.W)
        self.target_gender_var = tk.StringVar()
        gender_combo = ttk.Combobox(target_frame, textvariable=self.target_gender_var, width=10)
        gender_combo['values'] = ('ALL', 'M', 'F')
        gender_combo.grid(row=0, column=3, padx=5)

        ttk.Label(target_frame, text="年齡層:").grid(row=1, column=0, sticky=tk.W)
        self.target_age_var = tk.StringVar()
        age_combo = ttk.Combobox(target_frame, textvariable=self.target_age_var, width=15)
        age_combo['values'] = ('18-25', '26-35', '36-45', '46-55', '56-65', '65+', 'ALL')
        age_combo.grid(row=1, column=1, padx=5)

        ttk.Label(target_frame, text="優先順序:").grid(row=1, column=2, sticky=tk.W)
        self.priority_var = tk.IntVar()
        ttk.Spinbox(target_frame, from_=1, to=10, textvariable=self.priority_var, width=10).grid(row=1, column=3, padx=5)

        # 媒體檔案
        media_frame = ttk.LabelFrame(edit_frame, text="媒體檔案")
        media_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)

        ttk.Label(media_frame, text="圖片:").grid(row=0, column=0, sticky=tk.W)
        self.image_path_var = tk.StringVar()
        ttk.Entry(media_frame, textvariable=self.image_path_var, width=30).grid(row=0, column=1, padx=5)
        ttk.Button(media_frame, text="瀏覽", command=self.browse_image).grid(row=0, column=2)

        ttk.Label(media_frame, text="影片:").grid(row=1, column=0, sticky=tk.W)
        self.video_path_var = tk.StringVar()
        ttk.Entry(media_frame, textvariable=self.video_path_var, width=30).grid(row=1, column=1, padx=5)
        ttk.Button(media_frame, text="瀏覽", command=self.browse_video).grid(row=1, column=2)

        # 時間設定
        time_frame = ttk.LabelFrame(edit_frame, text="投放時間")
        time_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)

        ttk.Label(time_frame, text="開始日期:").grid(row=0, column=0, sticky=tk.W)
        self.start_date_var = tk.StringVar()
        ttk.Entry(time_frame, textvariable=self.start_date_var, width=15).grid(row=0, column=1, padx=5)

        ttk.Label(time_frame, text="結束日期:").grid(row=0, column=2, sticky=tk.W)
        self.end_date_var = tk.StringVar()
        ttk.Entry(time_frame, textvariable=self.end_date_var, width=15).grid(row=0, column=3, padx=5)

        # 狀態
        self.is_active_var = tk.BooleanVar()
        ttk.Checkbutton(time_frame, text="啟用廣告", variable=self.is_active_var).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=5)

        # 操作按鈕
        action_frame = ttk.Frame(edit_frame)
        action_frame.grid(row=5, column=0, columnspan=2, pady=20)

        ttk.Button(action_frame, text="儲存", command=self.save_advertisement).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="清除", command=self.clear_form).pack(side=tk.LEFT, padx=5)

        # 綁定樹狀檢視選取事件
        self.ad_tree.bind('<<TreeviewSelect>>', self.on_select)

        # 目前編輯的廣告ID
        self.current_ad_id = None

    def browse_image(self):
        filename = filedialog.askopenfilename(
            title="選擇圖片檔案",
            filetypes=[("圖片檔案", "*.jpg *.jpeg *.png *.gif *.bmp")]
        )
        if filename:
            # 複製檔案到廣告目錄
            basename = os.path.basename(filename)
            dest_path = os.path.join(self.ad_images_dir, basename)
            shutil.copy2(filename, dest_path)
            self.image_path_var.set(dest_path)

    def browse_video(self):
        filename = filedialog.askopenfilename(
            title="選擇影片檔案",
            filetypes=[("影片檔案", "*.mp4 *.avi *.mov *.mkv")]
        )
        if filename:
            basename = os.path.basename(filename)
            dest_path = os.path.join(self.ad_videos_dir, basename)
            shutil.copy2(filename, dest_path)
            self.video_path_var.set(dest_path)

    def load_advertisements(self):
        # 清空樹狀檢視
        for item in self.ad_tree.get_children():
            self.ad_tree.delete(item)

        if not self.db_connection:
            return

        cursor = self.db_connection.cursor()
        query = '''
            SELECT ad_id, title, target_category, target_gender, 
                   target_age_group, is_active 
            FROM advertisements 
            ORDER BY priority DESC, created_date DESC
        '''
        cursor.execute(query)

        for row in cursor:
            ad_id, title, category, gender, age_group, is_active = row
            status = "啟用" if is_active else "停用"
            self.ad_tree.insert('', 'end', values=(ad_id, title, category, gender, age_group, status))

        cursor.close()

    def on_select(self, event):
        selection = self.ad_tree.selection()
        if selection:
            item = self.ad_tree.item(selection[0])
            ad_id = item['values'][0]
            self.load_advertisement(ad_id)

    def load_advertisement(self, ad_id):
        cursor = self.db_connection.cursor()
        query = '''
            SELECT title, content, target_category, target_gender, target_age_group,
                   priority, image_path, video_path, start_date, end_date, is_active
            FROM advertisements WHERE ad_id = %s
        '''
        cursor.execute(query, (ad_id,))
        row = cursor.fetchone()
        cursor.close()

        if row:
            self.current_ad_id = ad_id
            title, content, category, gender, age_group, priority, image_path, video_path, start_date, end_date, is_active = row

            self.title_var.set(title or "")
            self.content_text.delete(1.0, tk.END)
            self.content_text.insert(1.0, content or "")
            self.category_var.set(category or "")
            self.target_gender_var.set(gender or "ALL")
            self.target_age_var.set(age_group or "")
            self.priority_var.set(priority or 1)
            self.image_path_var.set(image_path or "")
            self.video_path_var.set(video_path or "")
            self.start_date_var.set(str(start_date) if start_date else "")
            self.end_date_var.set(str(end_date) if end_date else "")
            self.is_active_var.set(bool(is_active))

    def clear_form(self):
        self.current_ad_id = None
        self.title_var.set("")
        self.content_text.delete(1.0, tk.END)
        self.category_var.set("")
        self.target_gender_var.set("ALL")
        self.target_age_var.set("")
        self.priority_var.set(1)
        self.image_path_var.set("")
        self.video_path_var.set("")
        self.start_date_var.set("")
        self.end_date_var.set("")
        self.is_active_var.set(True)

    def add_advertisement(self):
        self.clear_form()

    def edit_advertisement(self):
        selection = self.ad_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "請先選擇要編輯的廣告")
            return

        item = self.ad_tree.item(selection[0])
        ad_id = item['values'][0]
        self.load_advertisement(ad_id)

    def save_advertisement(self):
        # 驗證輸入
        if not self.title_var.get().strip():
            messagebox.showerror("錯誤", "請輸入廣告標題")
            return

        try:
            cursor = self.db_connection.cursor()

            if self.current_ad_id:
                # 更新現有廣告
                query = '''
                    UPDATE advertisements 
                    SET title=%s, content=%s, target_category=%s, target_gender=%s,
                        target_age_group=%s, priority=%s, image_path=%s, video_path=%s,
                        start_date=%s, end_date=%s, is_active=%s
                    WHERE ad_id=%s
                '''
                params = (
                    self.title_var.get().strip(),
                    self.content_text.get(1.0, tk.END).strip(),
                    self.category_var.get() or None,
                    self.target_gender_var.get(),
                    self.target_age_var.get() or None,
                    self.priority_var.get(),
                    self.image_path_var.get() or None,
                    self.video_path_var.get() or None,
                    self.start_date_var.get() or None,
                    self.end_date_var.get() or None,
                    self.is_active_var.get(),
                    self.current_ad_id
                )
            else:
                # 新增廣告
                query = '''
                    INSERT INTO advertisements 
                    (title, content, target_category, target_gender, target_age_group,
                     priority, image_path, video_path, start_date, end_date, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                '''
                params = (
                    self.title_var.get().strip(),
                    self.content_text.get(1.0, tk.END).strip(),
                    self.category_var.get() or None,
                    self.target_gender_var.get(),
                    self.target_age_var.get() or None,
                    self.priority_var.get(),
                    self.image_path_var.get() or None,
                    self.video_path_var.get() or None,
                    self.start_date_var.get() or None,
                    self.end_date_var.get() or None,
                    self.is_active_var.get()
                )

            cursor.execute(query, params)
            self.db_connection.commit()
            cursor.close()

            messagebox.showinfo("成功", "廣告儲存成功！")
            self.load_advertisements()

        except mysql.connector.Error as err:
            messagebox.showerror("資料庫錯誤", f"儲存失敗: {err}")

    def delete_advertisement(self):
        selection = self.ad_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "請先選擇要刪除的廣告")
            return

        if messagebox.askyesno("確認", "確定要刪除選中的廣告嗎？"):
            item = self.ad_tree.item(selection[0])
            ad_id = item['values'][0]

            try:
                cursor = self.db_connection.cursor()
                cursor.execute("DELETE FROM advertisements WHERE ad_id = %s", (ad_id,))
                self.db_connection.commit()
                cursor.close()

                messagebox.showinfo("成功", "廣告刪除成功！")
                self.load_advertisements()
                self.clear_form()

            except mysql.connector.Error as err:
                messagebox.showerror("資料庫錯誤", f"刪除失敗: {err}")

    def run(self):
        self.root.mainloop()

if __name__ == '__main__':
    app = AdManagerTool()
    app.run()
