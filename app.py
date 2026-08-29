import streamlit as st
import pandas as pd
from datetime import date

# Pengaturan Tampilan Layar (Responsif untuk HP & Desktop)
st.set_page_config(page_title="Kalender Pembebasan WBP", layout="wide")

st.title("🗓️ EWS & Kalender Pembebasan WBP")
st.caption("Aplikasi Pemantau Jadwal Kebebasan WBP Terintegrasi Data SDP")

# Sidebar untuk Unggah File Excel
st.sidebar.header("📁 Unggah Data Excel")
file_sdp = st.sidebar.file_uploader("1. Upload Data SDP (Master)", type=["xlsx", "csv"])
file_sk = st.sidebar.file_uploader("2. Upload Update SK Integrasi", type=["xlsx", "csv"])

# Proses Data jika File SDP Master diunggah
if file_sdp is not None:
    # Membaca Data SDP
    df_sdp = pd.read_excel(file_sdp) if file_sdp.name.endswith('.xlsx') else pd.read_csv(file_sdp)
    
    # Menyiapkan kolom tanggal bebas utama
    if 'Tgl_Bebas_Fix' not in df_sdp.columns:
        if 'Tanggal Ekspirasi' in df_sdp.columns:
            df_sdp['Tgl_Bebas_Fix'] = df_sdp['Tanggal Ekspirasi']
        else:
            df_sdp['Tgl_Bebas_Fix'] = None
        df_sdp['Status_SK'] = "Bebas Murni / Menunggu SK"

    # Memperbarui tanggal bebas jika ada file Update SK Integrasi
    if file_sk is not None:
        df_sk = pd.read_excel(file_sk) if file_sk.name.endswith('.xlsx') else pd.read_csv(file_sk)
        
        for index, row in df_sk.iterrows():
            no_reg = row['No Register']
            tgl_sk = row['Tanggal Bebas SK']
            no_sk = row.get('Nomor SK', 'SK Sah')
            
            mask = df_sdp['No Register'] == no_reg
            df_sdp.loc[mask, 'Tgl_Bebas_Fix'] = tgl_sk
            df_sdp.loc[mask, 'Status_SK'] = f"SK Turun ({no_sk})"
        
        st.sidebar.success("✅ Data SK Integrasi berhasil diperbarui!")

    # Format Kolom Tanggal
    df_sdp['Tgl_Bebas_Fix'] = pd.to_datetime(df_sdp['Tgl_Bebas_Fix']).dt.date
    today = date.today()

    # Navigasi Tab Tampilan
    tab1, tab2, tab3 = st.tabs(["🚨 Bebas Hari Ini", "📅 Rekap Pembebasan", "📱 Pencarian WBP (Mobile)"])

    # TAB 1: Dashboard Bebas Hari Ini
    with tab1:
        st.subheader(f"Pengingat Kebebasan Hari Ini ({today.strftime('%d %B %Y')})")
        bebas_hari_ini = df_sdp[df_sdp['Tgl_Bebas_Fix'] == today]
        
        if not bebas_hari_ini.empty:
            st.error(f"⚠️ ADA {len(bebas_hari_ini)} WBP YANG DIJADWALKAN BEBAS HARI INI!")
            kolom_tampil = [k for k in ['No Register', 'Nama', 'Jenis Pembebasan', 'Status_SK'] if k in df_sdp.columns]
            st.dataframe(bebas_hari_ini[kolom_tampil], use_container_width=True)
        else:
            st.success("✅ Tidak ada WBP yang dijadwalkan bebas hari ini.")

    # TAB 2: Rekapitulasi Pembebasan
    with tab2:
        st.subheader("Daftar Rekapitulasi Pembebasan WBP")
        kolom_pilihan = [k for k in ['No Register', 'Nama', 'Jenis Pembebasan', 'Tgl_Bebas_Fix', 'Status_SK'] if k in df_sdp.columns]
        st.dataframe(df_sdp[kolom_pilihan], use_container_width=True)

    # TAB 3: Direktori Mobile (HP Petugas)
    with tab3:
        st.subheader("🔍 Cari Identitas WBP")
        search = st.text_input("Ketik Nama atau No Register:")
        
        if search:
            hasil = df_sdp[
                df_sdp['Nama'].astype(str).str.contains(search, case=False, na=False) | 
                df_sdp['No Register'].astype(str).str.contains(search, case=False, na=False)
            ]
            
            if not hasil.empty:
                for _, wbp in hasil.iterrows():
                    with st.expander(f"👤 {wbp.get('Nama', '-')} ({wbp.get('No Register', '-')})", expanded=True):
                        st.write(f"**Jenis Pembebasan:** {wbp.get('Jenis Pembebasan', '-')}")
                        st.write(f"**Vonis:** {wbp.get('Vonis', '-')}")
                        st.write(f"**Tanggal 2/3:** {wbp.get('Tanggal 2/3', '-')}")
                        st.write(f"**Tanggal Ekspirasi:** {wbp.get('Tanggal Ekspirasi', '-')}")
                        st.write(f"**Status Kebebasan:** {wbp.get('Tgl_Bebas_Fix', '-')} ({wbp.get('Status_SK', '-')})")
            else:
                st.warning("Data WBP tidak ditemukan.")

else:
    st.info("👈 Silakan unggah file Excel SDP Master melalui menu di sidebar sebelah kiri untuk memulai.")
