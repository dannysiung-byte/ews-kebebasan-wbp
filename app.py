import streamlit as st
import pandas as pd
from datetime import date

st.set_page_config(page_title="Kalender Pembebasan WBP", layout="wide")

st.title("🗓️ EWS & Kalender Pembebasan WBP")
st.caption("Aplikasi Pemantau Jadwal Kebebasan WBP Terintegrasi Data SDP")

st.sidebar.header("📁 Unggah Data Excel")
file_sdp = st.sidebar.file_uploader("1. Upload Data SDP (Master)", type=["xlsx", "csv"])
file_sk = st.sidebar.file_uploader("2. Upload Update SK Integrasi", type=["xlsx", "csv"])

# Fungsi Pembaca File CSV/Excel yang Aman untuk SDP
def read_file(file):
    if file.name.endswith('.xlsx'):
        return pd.read_excel(file)
    else:
        # Menangani CSV SDP yang menggunakan titik koma (;) atau koma (,)
        try:
            return pd.read_csv(file, sep=';')
        except:
            return pd.read_csv(file, sep=',')

if file_sdp is not None:
    df_sdp = read_file(file_sdp)
    
    # LOGIKA PEMILAHAN OTOMATIS TANPA KOLOM JENIS PEMBEBASAN
    def deteksi_jenis_dan_tanggal(row):
        tgl_2_3 = row.get('Tanggal 2/3') or row.get('Tgl_2/3') or row.get('2/3') or row.get('TGL_2/3')
        tgl_eks = row.get('Tanggal Ekspirasi') or row.get('Tgl_Ekspirasi') or row.get('Ekspirasi') or row.get('TGL_EKSPIRASI')
        
        if pd.notna(tgl_2_3) and str(tgl_2_3).strip() not in ["-", "", "nan"]:
            jenis = "Integrasi (PB/CB/CMB)"
            tgl_bebas = tgl_2_3
        else:
            jenis = "Bebas Murni"
            tgl_bebas = tgl_eks
            
        return pd.Series([jenis, tgl_bebas])

    df_sdp[['Jenis_Pembebasan_Auto', 'Tgl_Bebas_Fix']] = df_sdp.apply(deteksi_jenis_dan_tanggal, axis=1)
    df_sdp['Status_SK'] = "Menunggu SK / Bebas Murni"

    if file_sk is not None:
        df_sk = read_file(file_sk)
        
        for index, row in df_sk.iterrows():
            no_reg = row.get('No Register') or row.get('NO_REGISTER')
            tgl_sk = row.get('Tanggal Bebas SK') or row.get('TGL_BEBAS_SK')
            no_sk = row.get('Nomor SK', 'SK Sah')
            
            mask = df_sdp.iloc[:, 0] == no_reg  # Mencari di kolom pertama jika nama beda
            if 'No Register' in df_sdp.columns:
                mask = df_sdp['No Register'] == no_reg
                
            df_sdp.loc[mask, 'Tgl_Bebas_Fix'] = tgl_sk
            df_sdp.loc[mask, 'Status_SK'] = f"SK Turun ({no_sk})"
        
        st.sidebar.success("✅ Data SK Integrasi berhasil diperbarui!")

    df_sdp['Tgl_Bebas_Fix'] = pd.to_datetime(df_sdp['Tgl_Bebas_Fix'], errors='coerce').dt.date
    today = date.today()

    tab1, tab2, tab3 = st.tabs(["🚨 Bebas Hari Ini", "📅 Rekap Pembebasan", "📱 Pencarian WBP (Mobile)"])

    with tab1:
        st.subheader(f"Pengingat Kebebasan Hari Ini ({today.strftime('%d %B %Y')})")
        bebas_hari_ini = df_sdp[df_sdp['Tgl_Bebas_Fix'] == today]
        
        if not bebas_hari_ini.empty:
            st.error(f"⚠️ ADA {len(bebas_hari_ini)} WBP YANG DIJADWALKAN BEBAS HARI INI!")
            st.dataframe(bebas_hari_ini, use_container_width=True)
        else:
            st.success("✅ Tidak ada WBP yang dijadwalkan bebas hari ini.")

    with tab2:
        st.subheader("Daftar Rekapitulasi Pembebasan WBP")
        st.dataframe(df_sdp, use_container_width=True)

    with tab3:
        st.subheader("🔍 Cari Identitas WBP")
        search = st.text_input("Ketik Nama atau No Register:")
        
        if search:
            # Mencari kata kunci di seluruh kolom teks
            hasil = df_sdp[df_sdp.astype(str).apply(lambda row: row.str.contains(search, case=False).any(), axis=1)]
            
            if not hasil.empty:
                st.dataframe(hasil, use_container_width=True)
            else:
                st.warning("Data WBP tidak ditemukan.")

else:
    st.info("👈 Silakan unggah file Excel/CSV SDP Master melalui menu di sidebar sebelah kiri untuk memulai.")
