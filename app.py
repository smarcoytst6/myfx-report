# app.py – pure production version (no Flask dev server)
from flask import Flask, request, jsonify
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')          # <-- fixes GUI-outside-main-thread warning
import matplotlib.pyplot as plt
from datetime import datetime
import json
import base64
from io import BytesIO

app = Flask(__name__)

def to_float(val, default=0.0):
    try:
        return float(val)
    except:
        return default

@app.route('/myfx_report', methods=['POST'])
def generate_report():
    try:
        data = request.get_json(silent=True) or {}
        live = data.get('account_info', {})
        trade_data = data.get('trade_data', {})

        # 帳戶資訊
        Broker = live.get('Broker', 'Unknown')
        Server = live.get('Server', 'Unknown')
        Number = live.get('Number', 'Unknown')
        Currency = live.get('Currency', 'Unknown')
        Equity = to_float(live.get('Equity', 0))
        Balance = to_float(live.get('Balance', 0))
        initial = to_float(live.get('Initial', 0))
        deposits = to_float(live.get('Deposits', 0))
        withdraws = to_float(live.get('Withdraws', 0))

        # 只取 Buy/Sell 交易
        trades = []
        for arr in trade_data.values():
            for t in arr if isinstance(arr, list) else []:
                if t.get('Type') in ['Buy', 'Sell']:
                    t['Profit'] = to_float(t.get('Profit', 0))
                    t['Commission'] = to_float(t.get('Commission', 0))
                    t['Swap'] = to_float(t.get('Swap', 0))
                    t['Ctime'] = to_float(t.get('Ctime', 0))
                    t['Ticket'] = t.get('Ticket', len(trades))
                    trades.append(t)
        df = pd.DataFrame(trades)

        if not df.empty:
            df['Ctime'] = pd.to_datetime(df['Ctime'], unit='s', errors='coerce')
            df = df.dropna(subset=['Ctime']).sort_values('Ctime').reset_index(drop=True)
            df['NetPL'] = df['Profit'] + df['Commission'] + df['Swap']
            df['CumProfit'] = df['NetPL'].cumsum()
        else:
            df['CumProfit'] = 0

        hist_balance = initial + deposits - withdraws + df['CumProfit']
        growth = hist_balance / hist_balance.iloc[0] * 100 if not df.empty else pd.Series([100])

        # 統計
        win_rate = len(df[df['Profit'] > 0]) / len(df) * 100 if not df.empty else 0
        peak = hist_balance.cummax()
        dd = hist_balance - peak
        max_dd_pct = abs(dd.min() / peak[dd.idxmin()] * 100) if not df.empty else 0

        stats = {
            'Equity': Equity,
            'Profit': df['NetPL'].sum() if not df.empty else 0,
            'WinRate': win_rate,
            'MaxDD_pct': max_dd_pct,
            'Growth': (Equity / initial - 1) * 100 if initial > 0 else 0
        }

        # ------------------- 畫圖 -------------------
        plt.rcParams['font.family'] = 'DejaVu Sans'
        fig = plt.figure(figsize=(20, 28), dpi=150, facecolor='white')
        gs = fig.add_gridspec(6, 2, hspace=0.5, wspace=0.3)

        # 1. 成長曲線
        ax1 = fig.add_subplot(gs[0, :])
        x_data = df['Ctime'] if not df.empty else [datetime.now()]
        ax1.fill_between(x_data, 100, growth, color='#4472C4', alpha=0.3)
        ax1.plot(x_data, growth, color='#4472C4', lw=5)
        ax1.set_title(f'{Broker}\n{Server} #{Number}\nGrowth → {stats["Growth"]:.1f}% • Equity ${Equity:,.0f}',
                      fontsize=30, fontweight='bold', color='#203864', pad=40)
        ax1.set_ylim(80, growth.max() + 30)
        ax1.axis('off')

        # 2. 橫條圖
        ax2 = fig.add_subplot(gs[1:3, 0])
        labels = [f'Equity\n${Equity:,.0f}', f'Profit\n${stats["Profit"]:,.0f}',
                  f'Initial\n${initial:,.0f}', f'Withdraws\n${withdraws:,.0f}', f'Deposit\n${deposits:,.0f}']
        values = [deposits, withdraws, initial, stats['Profit'], Equity]
        colors = ['#4472C4', '#FF5050', '#BFBFBF', '#00B0F0', '#00B050']
        bars = ax2.barh(labels, values, color=colors, height=0.7)
        for b in bars:
            ax2.text(b.get_width()+800, b.get_y()+0.25, f'{b.get_width():,.0f}', fontsize=15, fontweight='bold')
        ax2.set_xlim(0, max(values)*1.25)
        ax2.set_title('Account Summary ('+Currency+')', fontsize=20, pad=20)

        rich_labels = ['Deposits','Withdraws','Initial','Profit','Equity']
        ax2.set_yticks(range(len(rich_labels)))
        ax2.set_yticklabels(rich_labels, fontsize=12, linespacing=1.5, fontweight='bold')

        # 3. 雷達圖
        ax3 = fig.add_subplot(gs[1:3, 1], projection='polar')
        cats = ['Algo 98%', 'Win Rate', 'Activity 41.8%', 'Risk (1/DD)']
        vals = [98, stats['WinRate'], 41.8, 100 - stats['MaxDD_pct']] + [98]
        angles = np.linspace(0, 2*np.pi, 4, endpoint=False).tolist() + [0]
        ax3.plot(angles, vals, 'o-', lw=6, color='#1f77b4', markersize=12)
        ax3.fill(angles, vals, alpha=0.3, color='#1f77b4')
        ax3.set_xticks(angles[:-1])
        ax3.set_xticklabels([f'{c}\n{v:.1f}%'.replace('%','') for c,v in zip(cats, vals[:-1])], fontsize=15, fontweight='bold')
        ax3.set_yticks([]); ax3.set_ylim(0, 110); ax3.grid(True, lw=2); ax3.set_facecolor('#f8f9fa')

        # 4. Balance Curve
        ax4 = fig.add_subplot(gs[3:5, 0])
        if not df.empty:
            ax4.plot(df['Ctime'], hist_balance, color='#00B050', lw=5)
            ax4.fill_between(df['Ctime'], hist_balance, 0, color='#00B050', alpha=0.2)
        else:
            ax4.text(0.5, 0.5, 'Waiting for first trade...', transform=ax4.transAxes, fontsize=20, ha='center', color='#888')
        ax4.set_title('Balance Curve', fontsize=20); ax4.set_ylabel('USD'); ax4.grid(alpha=0.4)

        # 5. Growth %
        ax5 = fig.add_subplot(gs[3:5, 1])
        if not df.empty:
            ax5.plot(df['Ctime'], growth-100, color='#4472C4', lw=5)
            ax5.fill_between(df['Ctime'], growth-100, 0, color='#4472C4', alpha=0.2)
        else:
            ax5.text(0.5, 0.5, 'Waiting for first trade...', transform=ax5.transAxes, fontsize=20, ha='center', color='#888')
        ax5.set_title('Growth %', fontsize=20); ax5.set_ylabel('%'); ax5.grid(alpha=0.4)

        # 6. 月度 P&L 表格
        ax6 = fig.add_subplot(gs[5, :])
        ax6.axis('off')

        if df.empty:
            ax6.text(0.5, 0.5, 'No trades yet', transform=ax6.transAxes, ha='center', fontsize=20, color='#888')
            buf = BytesIO()
            fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
            buf.seek(0)
            b64 = base64.b64encode(buf.read()).decode()
            plt.close(fig)
            return jsonify({'base64_image': b64})

        df['Year'] = df['Ctime'].dt.year
        df['Month'] = df['Ctime'].dt.month
        monthly_pl = df.groupby(['Year', 'Month'])['NetPL'].sum().round(2)

        years = sorted(df['Year'].unique())
        current_year = datetime.now().year
        current_month = datetime.now().month

        col_labels = ['Year', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'YTD']
        table_data = []

        for year in years:
            row = [str(year)]
            year_sum = 0
            for m in range(1, 13):
                pl = monthly_pl.get((year, m), None)
                if pl is None:
                    row.append('')
                    continue
                pl = round(float(pl), 1)
                year_sum += pl
                if year == current_year and m > current_month:
                    row.append('')
                else:
                    row.append(f"{pl:+.1f}")
            row.append(f"{year_sum:+.1f}")
            table_data.append(row)

        for row in table_data:
            while len(row) < 14:
                row.append('')

        table = ax6.table(cellText=table_data,
                          colLabels=col_labels,
                          colWidths=[0.08] + [0.06]*12 + [0.08],
                          cellLoc='center',
                          loc='center',
                          bbox=[0.02, 0.05, 0.96, 0.9])

        table.auto_set_font_size(False)
        table.set_fontsize(12)
        table.scale(1, 2.3)

        for (i, j), cell in table.get_celld().items():
            cell.set_height(0.22)
            cell.set_linewidth(1.3)
            if i == 0:
                cell.set_facecolor('#1E40AF')
                cell.set_text_props(color='white', weight='bold', fontsize=13)
            elif j == 0:
                cell.set_facecolor('#DBEAFE')
                cell.set_text_props(weight='bold', color='#1E40AF')
            elif j == 13:
                cell.set_facecolor('#FEF3C7')
                cell.set_text_props(weight='bold', color='#92400E', fontsize=13)
            else:
                txt = cell.get_text().get_text()
                if txt:
                    if txt.startswith('+'):
                        cell.set_text_props(color='#166534', weight='bold')
                    elif txt.startswith('-'):
                        cell.set_text_props(color='#B91C1C', weight='bold')

        # ---------- 輸出 ----------
        buf = BytesIO()
        fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
        buf.seek(0)
        b64 = base64.b64encode(buf.read()).decode()
        plt.close(fig)
        return jsonify({'base64_image': b64})

    except Exception as e:
        return f"Error: {str(e)}", 500

# <--  **NO**  `if __name__ == '__main__'`  block here!