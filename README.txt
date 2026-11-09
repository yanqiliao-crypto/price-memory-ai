Price Memory AI 2.0 — Render 公開展示版（LightGBM + 樣本外 MDD）

用途：現有 Public GitHub repository + Render，完全不包含任何原始行情 CSV、模型權重或個別歷史價格序列。

新增功能：
- 獨立顯示真實歷史 LightGBM 2026 年三分類「平均預測機率」，不假裝為模擬 K 線當前預測。
- 2026 年非重疊 30 分鐘持有策略：最大回撤、累積報酬、交易次數、勝率，0/4/8 點來回成本切換。
- 完整呈現成本、成交假設及侷限。

2026 年樣本外：17,073 筆，Macro OvR AUC 0.652074。
策略：最高機率上漲做多、下跌做空、震盪不交易；每30分鐘一次決策不重疊部位，持有六根連續5分鐘K線。
100%名目部位、無槓桿、逐筆複利；以當根收盤買入/賣出、六根後收盤平倉（理想化成交）。
996筆交易；預設來回成本4點，累積報酬-0.36%，最大回撤-9.23%。
0點時累積+10.48%，MDD-7.47%；8點時累積-10.13%，MDD-11.78%。
此非真正期貨保證金帳戶報酬；未納交易滑價、價差波動、轉倉、未必可成交的收盤價。

部署：
1. 解壓縮本 ZIP。請上傳「資料夾裡的檔案」到原本 GitHub 公開專案 main 根目錄，不要上傳整個 ZIP。
2. 保留的檔案：server.py, index.html, requirements.txt, render.yaml, performance_summary.json, .gitignore, README.txt。
3. 絕不可上傳本機 Full.zip、data 資料夾、原始 CSV、模型 joblib。
4. Render 原設定：Build `pip install -r requirements.txt`，Start `python server.py`。
5. 確認 GitHub 主分支變更後，在 Render 按 Manual Deploy > Deploy latest commit（先前已關閉 Auto-Deploy）。
6. 網址 https://price-memory-ai.onrender.com/；用手機或學校電腦確認模擬行情字樣及 MDD 成本切換。

備註：即使只是摘要，資料或研究結果能否公開仍應遵守來源契約與老師/學校規定。
