import streamlit as st
import pandas as pd
from datetime import date
import os
import urllib.parse

st.set_page_config(page_title="SIP-WBP", layout="wide")

st.title("🗓️ SIP-WBP")
st.caption("Sistem Informasi Pemantauan & Kebebasan WBP Terintegrasi SDP")

FILE_MASTER_GITHUB = "master_sdp.xlsx"
FILE_CACHE_SDP = "data_sdp_terakhir.csv"
FILE_CACHE_SK = "data_sk_terakhir.csv"

st.sidebar.header("📁 Kelola Data SDP & SK")

file_sdp_upload = st.sidebar.file_uploader("1. Update Data SDP Master (Opsional)", type=["xlsx", "csv"])
file_sk_upload = st.sidebar.file_uploader("2. Upload Update SK Integrasi", type=["xlsx", "csv"])

def read_file(file):
    if hasattr(file, 'name') and file.name.endswith('.xlsx'):
        return pd.read_excel(file)
    elif isinstance(file, str) and file.endswith('.xlsx'):
        return pd.read_excel(file)
    else:
        try:
            return pd.read_csv(file, sep=';')
        except:
            return pd.read_csv(file, sep=',')

# Fungsi Konversi Tanggal Bahasa Indonesia & Berbagai Format
def parse_indo_date(series):
    bulan_indo = {
        'januari': 'january', 'februari': 'february', 'maret': 'march',
        'april': 'april', 'mei': 'may', 'juni': 'june',
        'juli': 'july', 'agustus': 'august', 'september': 'september',
        'oktober': 'october', 'november': 'november', 'desember': 'december'
    }
    
    s_clean = series.astype(str).str.lower()
    for indo, eng in bulan_indo.items():
        s_clean = s_clean.str.replace(indo, eng, regex=False)
        
    return pd.to_datetime(s_clean, errors='coerce', dayfirst=True).dt.date

df_sdp = None

if file_sdp_upload is not None:
    df_sdp = read_file(file_sdp_upload)
    df_sdp.to_csv(FILE_CACHE_SDP, index=False, sep=';')
    st.sidebar.success("💾 Data Master SDP baru berhasil diperbarui!")
elif os.path.exists(FILE_MASTER_GITHUB):
    df_sdp = read_file(FILE_MASTER_GITHUB)
    st.sidebar.success("✅ Terhubung dengan Master Data SDP (GitHub)")
elif os.path.exists(FILE_CACHE_SDP):
    df_sdp = pd.read_csv(FILE_CACHE_SDP, sep=';')
    st.sidebar.info("ℹ️ Menampilkan Data SDP Terakhir.")

if df_sdp is not None:
    col_reg = next((c for c in df_sdp.columns if 'REG' in c.upper()), df_sdp.columns[0])
    col_nama = next((c for c in df_sdp.columns if 'NAMA' in c.upper()), df_sdp.columns[1])
    col_2_3 = next((c for c in df_sdp.columns if '2/3' in c or 'dua tiga' in c.lower()), None)
    col_eks = next((c for c in df_sdp.columns if 'EKSPIRASI' in c.upper() or 'EKS' in c.upper()), None)
    
    # Filter Khusus Narapidana (Register B)
    df_sdp = df_sdp[df_sdp[col_reg].astype(str).str.strip().str.upper().str.startswith('B')].copy()

    # Ekstrim Tanggal Ekspirasi sebagai Patokan Awal
    if col_eks:
        df_sdp['Tgl_Bebas_Fix'] = parse_indo_date(df_sdp[col_eks])
    else:
        df_sdp['Tgl_Bebas_Fix'] = None

    if col_2_3:
        df_sdp['Tgl_2_3_Clean'] = parse_indo_date(df_sdp[col_2_3])

    df_sdp['Status_Kebebasan'] = "Bebas Murni (Patokan Ekspirasi)"

    if file_sk_upload is not None:
        df_sk = read_file(file_sk_upload)
        df_sk.to_csv(FILE_CACHE_SK, index=False, sep=';')
        st.sidebar.success("💾 Data SK Integrasi baru disimpan!")
    elif os.path.exists(FILE_CACHE_SK):
        df_sk = pd.read_csv(FILE_CACHE_SK, sep=';')
    else:
        df_sk = None

    if df_sk is not None:
        # Otomatis mengenali kolom REG, BEBAS/TGL, dan KET/SK
        col_sk_reg = next((c for c in df_sk.columns if 'REG' in c.upper()), df_sk.columns[0])
        col_sk_tgl = next((c for c in df_sk.columns if 'BEBAS' in c.upper() or 'TGL' in c.upper()), df_sk.columns[1])
        col_sk_ket = next((c for c in df_sk.columns if 'KET' in c.upper() or 'SK' in c.upper()), None)
        
        # Bersihkan Nomor Register (Hapus titik, spasi, & simbol di kedua dataset)
        df_sdp['reg_clean'] = df_sdp[col_reg].astype(str).str.upper().str.replace(r'[^A-Z0-9]', '', regex=True)
        df_sk['reg_clean'] = df_sk[col_sk_reg].astype(str).str.upper().str.replace(r'[^A-Z0-9]', '', regex=True)
        df_sk['Tgl_SK_Clean'] = parse_indo_date(df_sk[col_sk_tgl])
        
        for index, row in df_sk.iterrows():
            no_reg_sk = row['reg_clean']
            tgl_sk = row['Tgl_SK_Clean']
            
            # Ambil nilai KET (misal: CB / PB / CMB)
            if col_sk_ket and pd.notna(row[col_sk_ket]):
                no_sk = row[col_sk_ket]
            else:
                no_sk = 'SK Sah'
            
            mask = df_sdp['reg_clean'] == no_reg_sk
            if mask.any() and pd.notna(tgl_sk):
                df_sdp.loc[mask, 'Tgl_Bebas_Fix'] = tgl_sk
                df_sdp.loc[mask, 'Status_Kebebasan'] = f"SK Integrasi Turun ({no_sk})"

    today = date.today()

    tab1, tab2, tab3 = st.tabs(["🚨 EWS & Filter Tanggal", "📅 Rekap Pembebasan (Napi Only)", "📱 Pencarian WBP (Mobile)"])

    # --- TAB 1: EWS ---
    with tab1:
        st.subheader("🚨 Early Warning System Pembebasan Narapidana")
        col_tgl1, col_tgl2 = st.columns(2)
        with col_tgl1:
            tgl_mulai = st.date_input("Dari Tanggal:", today)
        with col_tgl2:
            tgl_selesai = st.date_input("Sampai Tanggal:", today)

        bebas_filtered = df_sdp[(df_sdp['Tgl_Bebas_Fix'] >= tgl_mulai) & (df_sdp['Tgl_Bebas_Fix'] <= tgl_selesai)]
        
        st.write("---")
        if not bebas_filtered.empty:
            st.warning(f"📌 Ditemukan **{len(bebas_filtered)} Narapidana (Reg B)** yang dijadwalkan bebas pada rentang tanggal tersebut.")
            kolom_tampil = [col_reg, col_nama, 'Tgl_Bebas_Fix', 'Status_Kebebasan']
            if col_2_3: kolom_tampil.append('Tgl_2_3_Clean')
            
            df_hasil = bebas_filtered[kolom_tampil].sort_values(by='Tgl_Bebas_Fix').reset_index(drop=True)
            df_hasil.index = df_hasil.index + 1
            df_hasil.index.name = "No"
            
            st.dataframe(df_hasil, use_container_width=True)

            tgl_str = f"{tgl_mulai.strftime('%d/%m/%Y')} s.d {tgl_selesai.strftime('%d/%m/%Y')}" if tgl_mulai != tgl_selesai else tgl_mulai.strftime('%d/%m/%Y')
            
            pesan_wa = f"📢 *LAPORAN EWS KEBEBASAN NARAPIDANA (SIP-WBP)*\n"
            pesan_wa += f"Periode: {tgl_str}\n"
            pesan_wa += "----------------------------------------\n"
            
            for idx, (_, row) in enumerate(df_hasil.iterrows(), start=1):
                pesan_wa += f"{idx}. *Nama*: {row[col_nama]}\n"
                pesan_wa += f"   *No Reg*: {row[col_reg]}\n"
                pesan_wa += f"   *Tgl Bebas*: {row['Tgl_Bebas_Fix']}\n"
                pesan_wa += f"   *Status*: {row['Status_Kebebasan']}\n\n"
                
            pesan_wa += f"----------------------------------------\n*Total*: {len(df_hasil)} Narapidana"
            
            encoded_wa = urllib.parse.quote(pesan_wa)
            wa_link = f"https://api.whatsapp.com/send?text={encoded_wa}"

            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                st.link_button("📲 Kirim / Salin Laporan ke WhatsApp", wa_link, type="primary")
            with col_btn2:
                csv_data = df_hasil.to_csv(index=True).encode('utf-8')
                st.download_button("📥 Unduh File Laporan (CSV/Excel)", data=csv_data, file_name=f"Laporan_Bebas_{tgl_mulai}.csv", mime="text/csv")
        else:
            st.success("✅ Tidak ada Narapidana yang dijadwalkan bebas pada rentang tanggal ini.")

    # --- TAB 2: REKAPITULASI ---
    with tab2:
        st.subheader("Daftar Rekapitulasi Pembebasan Narapidana (Reg B)")
        kolom_utama = [col_reg, col_nama, 'Tgl_Bebas_Fix', 'Status_Kebebasan']
        if col_2_3: kolom_utama.insert(2, 'Tgl_2_3_Clean')
        if col_eks: kolom_utama.insert(3, col_eks)
        
        df_tampil = df_sdp[kolom_utama].copy()
        if 'Tgl_2_3_Clean' in df_tampil.columns:
            df_tampil.rename(columns={'Tgl_2_3_Clean': 'Tanggal 2/3 (Mulai Pengurusan)'}, inplace=True)
            
        df_tampil_sorted = df_tampil.sort_values(by='Tgl_Bebas_Fix').reset_index(drop=True)
        df_tampil_sorted.index = df_tampil_sorted.index + 1
        df_tampil_sorted.index.name = "No"

        st.dataframe(df_tampil_sorted, use_container_width=True)

    # --- TAB 3: MOBILE ---
    with tab3:
        st.subheader("🔍 Cari Identitas Narapidana (Reg B)")
        search = st.text_input("Ketik Nama atau No Register:")
        
        if search:
            hasil = df_sdp[
                df_sdp[col_nama].astype(str).str.contains(search, case=False, na=False) | 
                df_sdp[col_reg].astype(str).str.contains(search, case=False, na=False)
            ]
            
            if not hasil.empty:
                for _, wbp in hasil.iterrows():
                    with st.expander(f"👤 {wbp[col_nama]} ({wbp[col_reg]})", expanded=True):
                        st.write(f"**Status:** {wbp['Status_Kebebasan']}")
                        st.write(f"**Tanggal Bebas Fix:** :green[{wbp['Tgl_Bebas_Fix']}]")
                        if col_2_3: st.write(f"**Tanggal 2/3 (Mulai Pengurusan):** {wbp.get('Tgl_2_3_Clean', '-')}")
                        if col_eks: st.write(f"**Tanggal Ekspirasi Murni:** {wbp.get(col_eks, '-')}")
            else:
                st.warning("Data Narapidana tidak ditemukan (Atau statusnya masih Tahanan / Reg A).")

else:
    st.info("👈 Silakan unggah file Excel/CSV SDP Master melalui menu di sidebar sebelah kiri untuk memulai.")
