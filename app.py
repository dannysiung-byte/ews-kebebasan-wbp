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
        try:
            return pd.read_csv(file, sep=';')
        except:
            return pd.read_csv(file, sep=',')

if file_sdp is not None:
    df_sdp = read_file(file_sdp)
    
    # Cari Nama Kolom Tanggal & Register Secara Dinamis
    col_reg = next((c for c in df_sdp.columns if 'REG' in c.upper()), df_sdp.columns[0])
    col_nama = next((c for c in df_sdp.columns if 'NAMA' in c.upper()), df_sdp.columns[1])
    col_2_3 = next((c for c in df_sdp.columns if '2/3' in c or 'dua tiga' in c.lower()), None)
    col_eks = next((c for c in df_sdp.columns if 'EKSPIRASI' in c.upper() or 'EKS' in c.upper()), None)
    
    # Menentukan Jenis Pembebasan & Tanggal Bebas Utama
    def deteksi_jenis_dan_tanggal(row):
        tgl_2_3 = row.get(col_2_3) if col_2_3 else None
        tgl_eks = row.get(col_eks) if col_eks else None
        
        # Bebas Murni selalu menggunakan Tanggal Ekspirasi
        if pd.notna(tgl_2_3) and str(tgl_2_3).strip() not in ["-", "", "nan"]:
            jenis = "Integrasi (PB/CB/CMB)"
            tgl_bebas = tgl_2_3
        else:
            jenis = "Bebas Murni"
            tgl_bebas = tgl_eks  # Berpatokan pada Tanggal Ekspirasi Akhir
            
        return pd.Series([jenis, tgl_bebas])

    df_sdp[['Kategori_Bebas', 'Tgl_Bebas_Fix']] = df_sdp.apply(deteksi_jenis_dan_tanggal, axis=1)
    df_sdp['Status_SK'] = "Menunggu SK / Estimasi"

    # Proses Update dari File SK Integrasi
    if file_sk is not None:
        df_sk = read_file(file_sk)
        col_sk_reg = next((c for c in df_sk.columns if 'REG' in c.upper()), df_sk.columns[0])
        col_sk_tgl = next((c for c in df_sk.columns if 'BEBAS' in c.upper() or 'TGL' in c.upper()), df_sk.columns[1])
        
        for index, row in df_sk.iterrows():
            no_reg = row[col_sk_reg]
            tgl_sk = row[col_sk_tgl]
            no_sk = row.get('Nomor SK', 'SK Sah')
            
            mask = df_sdp[col_reg] == no_reg
            df_sdp.loc[mask, 'Tgl_Bebas_Fix'] = tgl_sk
            df_sdp.loc[mask, 'Status_SK'] = f"SK Turun ({no_sk})"
        
        st.sidebar.success("✅ Data SK Integrasi berhasil diperbarui!")

    # Format Tanggal ke format date Python
    df_sdp['Tgl_Bebas_Fix'] = pd.to_datetime(df_sdp['Tgl_Bebas_Fix'], errors='coerce').dt.date
    today = date.today()

    tab1, tab2, tab3 = st.tabs(["🚨 EWS & Filter Tanggal", "📅 Rekap Pembebasan", "📱 Pencarian WBP (Mobile)"])

    # --- TAB 1: EWS & PENCARIAN BERDASARKAN TANGGAL ---
    with tab1:
        st.subheader("🚨 Early Warning System & Filter Kebebasan")
        
        # Filter Pemilih Tanggal
        col_tgl1, col_tgl2 = st.columns(2)
        with col_tgl1:
            tgl_mulai = st.date_input("Dari Tanggal:", today)
        with col_tgl2:
            tgl_selesai = st.date_input("Sampai Tanggal:", today)

        # Filter Data berdasarkan rentang tanggal pilihan
        bebas_filtered = df_sdp[(df_sdp['Tgl_Bebas_Fix'] >= tgl_mulai) & (df_sdp['Tgl_Bebas_Fix'] <= tgl_selesai)]
        
        st.write("---")
        if not bebas_filtered.empty:
            st.warning(f"📌 Ditemukan **{len(bebas_filtered)} WBP** yang dijadwalkan bebas pada rentang tanggal tersebut.")
            
            kolom_tampil = [col_reg, col_nama, 'Kategori_Bebas', 'Tgl_Bebas_Fix', 'Status_SK']
            if col_eks: kolom_tampil.append(col_eks)
            
            st.dataframe(bebas_filtered[kolom_tampil].sort_values(by='Tgl_Bebas_Fix'), use_container_width=True)
        else:
            st.success("✅ Tidak ada WBP yang dijadwalkan bebas pada rentang tanggal ini.")

    # --- TAB 2: REKAPITULASI PEMBEBASAN ---
    with tab2:
        st.subheader("Daftar Rekapitulasi Pembebasan WBP")
        kolom_utama = [col_reg, col_nama, 'Kategori_Bebas', 'Tgl_Bebas_Fix', 'Status_SK']
        if col_2_3: kolom_utama.append(col_2_3)
        if col_eks: kolom_utama.append(col_eks)
        
        st.dataframe(df_sdp[kolom_utama].sort_values(by='Tgl_Bebas_Fix'), use_container_width=True)

    # --- TAB 3: TAMPILAN MOBILE ---
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
                        st.write(f"**Kategori:** {wbp['Kategori_Bebas']}")
                        st.write(f"**Tanggal Bebas Fix:** :green[{wbp['Tgl_Bebas_Fix']}]")
                        st.write(f"**Status SK:** {wbp['Status_SK']}")
                        if col_eks: st.write(f"**Tanggal Ekspirasi (Murni):** {wbp.get(col_eks, '-')}")
            else:
                st.warning("Data WBP tidak ditemukan.")

else:
    st.info("👈 Silakan unggah file Excel/CSV SDP Master melalui menu di sidebar sebelah kiri untuk memulai.")
