import streamlit as st
import pandas as pd
from datetime import date

st.set_page_config(page_title="Kalender Pembebasan WBP", layout="wide")

st.title("🗓️ EWS & Kalender Pembebasan WBP")
st.caption("Aplikasi Pemantau Jadwal Kebebasan WBP Terintegrasi Data SDP")

st.sidebar.header("📁 Unggah Data Excel")
file_sdp = st.sidebar.file_uploader("1. Upload Data SDP (Master)", type=["xlsx", "csv"])
file_sk = st.sidebar.file_uploader("2. Upload Update SK Integrasi", type=["xlsx", "csv"])

if file_sdp is not None:
    df_sdp = pd.read_excel(file_sdp) if file_sdp.name.endswith('.xlsx') else pd.read_csv(file_sdp)
    
    # --- LOGIKA PEMILAHAN OTOMATIS TANPA KOLOM JENIS PEMBEBASAN ---
    def deteksi_jenis_dan_tanggal(row):
        tgl_2_3 = row.get('Tanggal 2/3') or row.get('Tgl_2/3') or row.get('2/3')
        tgl_eks = row.get('Tanggal Ekspirasi') or row.get('Tgl_Ekspirasi') or row.get('Ekspirasi')
        
        # Jika ada tanggal 2/3, kategorikan sebagai Integrasi
        if pd.notna(tgl_2_3) and str(tgl_2_3).strip() != "-" and str(tgl_2_3).strip() != "":
            jenis = "Integrasi (PB/CB/CMB)"
            tgl_bebas = tgl_2_3  # Tanggal perkiraan sebelum SK turun
        else:
            jenis = "Bebas Murni"
            tgl_bebas = tgl_eks
            
        return pd.Series([jenis, tgl_bebas])

    # Terapkan pemilahan otomatis
    df_sdp[['Jenis_Pembebasan_Auto', 'Tgl_Bebas_Fix']] = df_sdp.apply(deteksi_jenis_dan_tanggal, axis=1)
    df_sdp['Status_SK'] = "Menunggu SK / Bebas Murni"

    # Update data jika ada SK Turun
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

    # Format Tanggal
    df_sdp['Tgl_Bebas_Fix'] = pd.to_datetime(df_sdp['Tgl_Bebas_Fix'], errors='coerce').dt.date
    today = date.today()

    # Navigasi Tab Tampilan
    tab1, tab2, tab3 = st.tabs(["🚨 Bebas Hari Ini", "📅 Rekap Pembebasan", "📱 Pencarian WBP (Mobile)"])

    with tab1:
        st.subheader(f"Pengingat Kebebasan Hari Ini ({today.strftime('%d %B %Y')})")
        bebas_hari_ini = df_sdp[df_sdp['Tgl_Bebas_Fix'] == today]
        
        if not bebas_hari_ini.empty:
            st.error(f"⚠️ ADA {len(bebas_hari_ini)} WBP YANG DIJADWALKAN BEBAS HARI INI!")
            st.dataframe(bebas_hari_ini[['No Register', 'Nama', 'Jenis_Pembebasan_Auto', 'Status_SK']], use_container_width=True)
        else:
            st.success("✅ Tidak ada WBP yang dijadwalkan bebas hari ini.")

    with tab2:
        st.subheader("Daftar Rekapitulasi Pembebasan WBP")
        st.dataframe(df_sdp[['No Register', 'Nama', 'Jenis_Pembebasan_Auto', 'Tgl_Bebas_Fix', 'Status_SK']], use_container_width=True)

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
                        st.write(f"**Kategori:** {wbp.get('Jenis_Pembebasan_Auto', '-')}")
                        st.write(f"**Tanggal Bebas Saat Ini:** {wbp.get('Tgl_Bebas_Fix', '-')}")
                        st.write(f"**Status SK:** {wbp.get('Status_SK', '-')}")
            else:
                st.warning("Data WBP tidak ditemukan.")

else:
    st.info("👈 Silakan unggah file Excel SDP Master melalui menu di sidebar sebelah kiri untuk memulai.")
