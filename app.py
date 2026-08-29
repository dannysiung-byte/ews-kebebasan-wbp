import streamlit as st
import pandas as pd
from datetime import date
import os

st.set_page_config(page_title="Kalender Pembebasan WBP", layout="wide")

st.title("🗓️ EWS & Kalender Pembebasan WBP")
st.caption("Aplikasi Pemantau Jadwal Kebebasan WBP Terintegrasi Data SDP")

# Nama File Penyimpanan Permanen di Server
FILE_CACHE_SDP = "data_sdp_terakhir.csv"
FILE_CACHE_SK = "data_sk_terakhir.csv"

st.sidebar.header("📁 Unggah Data Excel")
file_sdp = st.sidebar.file_uploader("1. Upload Data SDP (Master)", type=["xlsx", "csv"])
file_sk = st.sidebar.file_uploader("2. Upload Update SK Integrasi", type=["xlsx", "csv"])

# Fungsi Pembaca File CSV/Excel SDP
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

# --- LOGIKA PENYIMPANAN DATA PERMANEN ---
df_sdp = None

# 1. Jika User Mengunggah File SDP Baru
if file_sdp is not None:
    df_sdp = read_file(file_sdp)
    # Simpan ke server sebagai cache permanen
    df_sdp.to_csv(FILE_CACHE_SDP, index=False, sep=';')
    st.sidebar.success("💾 Data Master SDP baru berhasil disimpan!")

# 2. Jika Tidak Ada Upload Baru, Muat Data Terakhir yang Pernah Disimpan
elif os.path.exists(FILE_CACHE_SDP):
    df_sdp = pd.read_csv(FILE_CACHE_SDP, sep=';')
    st.sidebar.info("ℹ️ Menampilkan Data SDP Terakhir yang Tersimpan.")

# --- JIKA DATA SDP TERSEDIA ---
if df_sdp is not None:
    col_reg = next((c for c in df_sdp.columns if 'REG' in c.upper()), df_sdp.columns[0])
    col_nama = next((c for c in df_sdp.columns if 'NAMA' in c.upper()), df_sdp.columns[1])
    col_2_3 = next((c for c in df_sdp.columns if '2/3' in c or 'dua tiga' in c.lower()), None)
    col_eks = next((c for c in df_sdp.columns if 'EKSPIRASI' in c.upper() or 'EKS' in c.upper()), None)
    
    # Patokan Utama Kebebasan Murni pada Tanggal Ekspirasi
    df_sdp['Tgl_Bebas_Fix'] = df_sdp[col_eks] if col_eks else None
    df_sdp['Status_Kebebasan'] = "Bebas Murni (Patokan Ekspirasi)"

    # --- LOGIKA SK INTEGRASI ---
    if file_sk is not None:
        df_sk = read_file(file_sk)
        df_sk.to_csv(FILE_CACHE_SK, index=False, sep=';')
        st.sidebar.success("💾 Data SK Integrasi baru disimpan!")
    elif os.path.exists(FILE_CACHE_SK):
        df_sk = pd.read_csv(FILE_CACHE_SK, sep=';')
    else:
        df_sk = None

    if df_sk is not None:
        col_sk_reg = next((c for c in df_sk.columns if 'REG' in c.upper()), df_sk.columns[0])
        col_sk_tgl = next((c for c in df_sk.columns if 'BEBAS' in c.upper() or 'TGL' in c.upper()), df_sk.columns[1])
        
        for index, row in df_sk.iterrows():
            no_reg = row[col_sk_reg]
            tgl_sk = row[col_sk_tgl]
            no_sk = row.get('Nomor SK', 'SK Sah')
            
            mask = df_sdp[col_reg] == no_reg
            df_sdp.loc[mask, 'Tgl_Bebas_Fix'] = tgl_sk
            df_sdp.loc[mask, 'Status_Kebebasan'] = f"SK Integrasi Turun ({no_sk})"

    # Format Tanggal
    df_sdp['Tgl_Bebas_Fix'] = pd.to_datetime(df_sdp['Tgl_Bebas_Fix'], errors='coerce').dt.date
    if col_2_3:
        df_sdp['Tgl_2_3_Clean'] = pd.to_datetime(df_sdp[col_2_3], errors='coerce').dt.date

    today = date.today()

    tab1, tab2, tab3 = st.tabs(["🚨 EWS & Filter Tanggal", "📅 Rekap Pembebasan", "📱 Pencarian WBP (Mobile)"])

    # --- TAB 1: EWS ---
    with tab1:
        st.subheader("🚨 Early Warning System Pembebasan")
        col_tgl1, col_tgl2 = st.columns(2)
        with col_tgl1:
            tgl_mulai = st.date_input("Dari Tanggal:", today)
        with col_tgl2:
            tgl_selesai = st.date_input("Sampai Tanggal:", today)

        bebas_filtered = df_sdp[(df_sdp['Tgl_Bebas_Fix'] >= tgl_mulai) & (df_sdp['Tgl_Bebas_Fix'] <= tgl_selesai)]
        
        st.write("---")
        if not bebas_filtered.empty:
            st.warning(f"📌 Ditemukan **{len(bebas_filtered)} WBP** yang dijadwalkan bebas pada rentang tanggal tersebut.")
            kolom_tampil = [col_reg, col_nama, 'Tgl_Bebas_Fix', 'Status_Kebebasan']
            if col_2_3: kolom_tampil.append('Tgl_2_3_Clean')
            st.dataframe(bebas_filtered[kolom_tampil].sort_values(by='Tgl_Bebas_Fix'), use_container_width=True)
        else:
            st.success("✅ Tidak ada WBP yang dijadwalkan bebas pada rentang tanggal ini.")

    # --- TAB 2: REKAPITULASI ---
    with tab2:
        st.subheader("Daftar Rekapitulasi Pembebasan & Pengurusan Integrasi")
        kolom_utama = [col_reg, col_nama, 'Tgl_Bebas_Fix', 'Status_Kebebasan']
        if col_2_3: kolom_utama.insert(2, 'Tgl_2_3_Clean')
        if col_eks: kolom_utama.insert(3, col_eks)
        
        df_tampil = df_sdp[kolom_utama].copy()
        if 'Tgl_2_3_Clean' in df_tampil.columns:
            df_tampil.rename(columns={'Tgl_2_3_Clean': 'Tanggal 2/3 (Awal Pengurusan)'}, inplace=True)
            
        st.dataframe(df_tampil.sort_values(by='Tgl_Bebas_Fix'), use_container_width=True)

    # --- TAB 3: MOBILE ---
    with tab3:
        st.subheader("🔍 Cari Identitas WBP")
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
                st.warning("Data WBP tidak ditemukan.")

else:
    st.info("👈 Silakan unggah file Excel/CSV SDP Master melalui menu di sidebar sebelah kiri untuk memulai.")
