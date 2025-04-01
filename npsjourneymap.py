import streamlit as st
import pandas as pd
import string
from unidecode import unidecode
from textblob import TextBlob
import io
import matplotlib.pyplot as plt
from pandas import ExcelWriter
from collections import Counter

st.set_page_config(page_title="Journey Map Dinámico", layout="wide")
st.title("📊 VQ Journey Map Dinámico")

# --- FUNCIONES ---

def limpiar_texto(texto):
    if pd.isna(texto):
        return ""
    texto = str(texto).lower()
    texto = unidecode(texto)
    texto = texto.translate(str.maketrans('', '', string.punctuation))
    return texto

def clasificar_etapa(texto):
    texto = limpiar_texto(texto)
    if any(p in texto for p in ["alta", "instalacion", "instalar", "bienvenida", "nuevo cliente", "activacion"]):
        return "Inicio de relación"
    elif any(p in texto for p in ["corte", "sin servicio", "tecnico", "reparacion", "fallo", "soporte", "problema tecnico", "visita"]):
        return "Soporte técnico"
    elif any(p in texto for p in ["plan", "factura", "cambio", "tarifa", "cobro", "error", "compra", "comercial", "asesor"]):
        return "Gestión comercial"
    elif any(p in texto for p in ["renovar", "retener", "descuento", "me ofrecieron", "baja", "cancelar", "promocion"]):
        return "Renovación / retención"
    elif any(p in texto for p in ["satisfecho", "recomiendo", "mala experiencia", "encuesta", "opinion", "mejorar"]):
        return "Voz del cliente"
    else:
        return "Sin clasificar"

def analizar_sentimiento(texto):
    if not texto or pd.isna(texto):
        return "No aplica"

    try:
        texto_traducido = str(TextBlob(texto).translate(to='en'))
        polaridad = TextBlob(texto_traducido).sentiment.polarity
    except Exception:
        polaridad = TextBlob(texto).sentiment.polarity

    if polaridad > 0.1:
        sentimiento = "Positivo"
    elif polaridad < -0.1:
        sentimiento = "Negativo"
    else:
        sentimiento = "Neutro"

    palabras = limpiar_texto(texto).split()
    if len(palabras) > 25 and sentimiento != "Positivo":
        sentimiento = "Negativo"

    return sentimiento

def map_emocion(sent):
    if sent == "Positivo":
        return "😍 Satisfacción"
    elif sent == "Negativo":
        return "😠 Frustración"
    else:
        return "😐 Neutro"

def detectar_necesidades_multiples(texto):
    texto = texto.lower()
    necesidades = []

    if any(p in texto for p in ["turno", "visita", "instalación", "cita técnica", "domiciliaria", "técnico", "asistencia", "asistieron", "conectar"]):
        necesidades.append("Mejorar cumplimiento en visitas técnicas")

    if any(p in texto for p in ["cortes", "sin servicio", "corte", "caída", "intermitente", "fibra", "cable", "streaming"]):
        necesidades.append("Reducir cortes y mejorar estabilidad del servicio")

    if any(p in texto for p in ["lenta", "demora", "tardanza", "espera", "tiempo"]):
        necesidades.append("Reducir tiempos de atención")

    if any(p in texto for p in ["factura", "error", "precio", "cobro", "importe", "monto", "promo", "descuentos", "tarifas", "promociones"]):
        necesidades.append("Optimizar facturación y cobros")

    if any(p in texto for p in ["operador", "amable", "buena", "excelente", "cordial", "trato", "bien atendido", "muy bien atendido", "genial", "buen servicio", "no tengo problema", "no tengo inconveniente", "satisfecho", "funciona bien"]):
        necesidades.append("Mantener calidad atención telefónica")

    if any(p in texto for p in ["maltrato", "mala atención", "grosero", "pésima atención", "maleducado", "desagradable", "trato deficiente", "sin respeto", "insatisfecho", "mal educado", "pésimo servicio"]):
        necesidades.append("Mejorar calidad de atención telefónica")

    if any(p in texto for p in ["reclamo", "solución", "resolver", "problema", "la señal", "no funciona", "baja", "buen servicio tecnico", "mal servicio tecnico"]):
        necesidades.append("Funcionamiento del servicio")     
    

    if len(necesidades) == 0:
        necesidades.append("Revisar manualmente")

    return "; ".join(necesidades)

kpi_sugerido = {
    "Inicio de relación": "Tiempo de activación, tasa de instalación",
    "Soporte técnico": "Tasa de resolución en primer contacto, visitas",
    "Gestión comercial": "Tiempos de gestión, satisfacción comercial",
    "Renovación / retención": "% retención, tasa de churn",
    "Voz del cliente": "NPS, sentimiento, viralidad"
}

accion_sugerida = {
    "Inicio de relación": "Registrar como best practice. Reconocer al técnico.",
    "Soporte técnico": "Activar visita técnica urgente. Seguimiento post-visita.",
    "Gestión comercial": "Revisar reglas de facturación. Enviar resumen explicativo.",
    "Renovación / retención": "Auditar ofertas de retención. Evaluar efectividad del beneficio.",
    "Voz del cliente": "Escalar mejoras o reconocer buena atención."
}

# --- CARGA DE ARCHIVO ---

archivo = st.file_uploader("📁 Subí tu archivo CSV", type=["csv"])

if archivo is not None:
    df = pd.read_csv(archivo)

    if 'verbatims' not in df.columns or 'fecha' not in df.columns or 'dni' not in df.columns:
        st.error("El archivo debe tener columnas: 'verbatims', 'fecha' y 'dni'.")
    else:
        df = df.dropna(subset=['verbatims']).copy()
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
        df['Etapa del Journey'] = df['verbatims'].apply(clasificar_etapa)
        df['Sentimiento'] = df['verbatims'].apply(analizar_sentimiento)
        df["Necesidad Detectada"] = df['verbatims'].apply(detectar_necesidades_multiples)

        df["🎭 Emoción"] = df["Sentimiento"].apply(map_emocion)
        df["📈 KPI Asociado"] = df["Etapa del Journey"].map(kpi_sugerido)
        df["✅ Acción Sugerida"] = df["Etapa del Journey"].map(accion_sugerida)

        df = df.rename(columns={"verbatims": "💬 Verbatim de ejemplo"})
        
      
        # --- FILTROS ---
        st.sidebar.header("🎛️ Filtros Journey Map")

        min_fecha = df["fecha"].min()
        max_fecha = df["fecha"].max()
        fecha_sel = st.sidebar.date_input("📅 Filtrar por fecha", [min_fecha, max_fecha], min_value=min_fecha, max_value=max_fecha)

        etapas = df["Etapa del Journey"].unique().tolist()
        sentimientos = df["Sentimiento"].unique().tolist()
        emociones = df["🎭 Emoción"].unique().tolist()
        kpis = df["📈 KPI Asociado"].dropna().unique().tolist()

        etapa_sel = st.sidebar.multiselect("🧭 Etapa del Journey", etapas, default=etapas)
        senti_sel = st.sidebar.multiselect("🧠 Sentimiento", sentimientos, default=sentimientos)
        emo_sel = st.sidebar.multiselect("🎭 Emoción", emociones, default=emociones)
        kpi_sel = st.sidebar.multiselect("📈 KPI Asociado", kpis, default=kpis)

        df_filtrado = df[
            (df["fecha"] >= pd.to_datetime(fecha_sel[0])) &
            (df["fecha"] <= pd.to_datetime(fecha_sel[1])) &
            (df["Etapa del Journey"].isin(etapa_sel)) &
            (df["Sentimiento"].isin(senti_sel)) &
            (df["🎭 Emoción"].isin(emo_sel)) &
            (df["📈 KPI Asociado"].isin(kpi_sel))
        ]

        # --- TABLA FINAL ---
        st.subheader("🗺️ Mapa de Flujo: Verbatim → Necesidad → Etapa → Acción")
        columnas_finales = ["💬 Verbatim de ejemplo", "Necesidad Detectada", "Etapa del Journey", "📈 KPI Asociado", "✅ Acción Sugerida"]
        st.dataframe(df_filtrado[columnas_finales], use_container_width=True)

        # --- EXPORTAR A EXCEL ---
        buffer = io.BytesIO()
        with ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df_filtrado.to_excel(writer, index=False, sheet_name='Verbatims')
        st.download_button("💾 Descargar Excel filtrado", data=buffer.getvalue(), file_name="journey_map_filtrado.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        # --- GRÁFICO DE NECESIDADES ---
        st.subheader("📊 Distribución de Necesidades Detectadas")
        necesidades_explode = df_filtrado['Necesidad Detectada'].str.split(';').explode().str.strip()
        necesidades_explode = necesidades_explode[necesidades_explode != ""]
        conteo_necesidades = necesidades_explode.value_counts()
        fig, ax = plt.subplots(figsize=(10, len(conteo_necesidades)*0.3))
        conteo_necesidades.plot(kind='barh', ax=ax, color='steelblue')
        ax.set_title("Necesidades más frecuentes")
        ax.set_xlabel("Cantidad")
        st.pyplot(fig)

        # --- VERBATIMS PARA REVISAR ---
        st.subheader("🔍 Verbatims para Revisar Manualmente")
        revisar_df = df_filtrado[df_filtrado['Necesidad Detectada'].str.contains("Revisar manualmente")]
        if not revisar_df.empty:
            st.dataframe(revisar_df[['fecha', 'dni', '💬 Verbatim de ejemplo']])
        else:
            st.info("No hay verbatims para revisar manualmente.")

        # --- DASHBOARD RESUMEN ---
        st.subheader("📈 Resumen por Etapa y Emoción")
        resumen = df_filtrado.groupby(['Etapa del Journey', '🎭 Emoción']).size().unstack(fill_value=0)
        st.dataframe(resumen)
        


        # --- DESCARGAR VERBATIMS A REVISAR ---
        if not revisar_df.empty:
            buffer_revisar = io.BytesIO()
            with ExcelWriter(buffer_revisar, engine='xlsxwriter') as writer:
                revisar_df.to_excel(writer, index=False, sheet_name='Para Revisar')
            st.download_button(
                label="📥 Descargar verbatims para revisar",
                data=buffer_revisar.getvalue(),
                file_name="verbatims_para_revisar.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
        # --- NUEVO BLOQUE: AGRUPACIÓN DE VERBATIMS PARA REVISAR ---
        st.subheader("🧩 Agrupación de Verbatims a Revisar por Palabras Clave")

        if not revisar_df.empty:
            revisar_df['texto_limpio'] = revisar_df['💬 Verbatim de ejemplo'].apply(limpiar_texto)
            palabras = " ".join(revisar_df['texto_limpio']).split()
            conteo = Counter(palabras)
            palabras_comunes = [p for p, c in conteo.items() if c > 1 and len(p) > 3][:20]
            st.write("Palabras más comunes entre los verbatims sin clasificar:")
            st.write(palabras_comunes)

            palabra_seleccionada = st.selectbox("🔎 Seleccioná una palabra clave para ver ejemplos:", palabras_comunes)
            verbatims_con_palabra = revisar_df[revisar_df['texto_limpio'].str.contains(palabra_seleccionada)]
            st.write(f"Verbatims que contienen la palabra '{palabra_seleccionada}':")
            st.dataframe(verbatims_con_palabra[['fecha', 'dni', '💬 Verbatim de ejemplo']])
            

            # --- BLOQUE: N-Gramas frecuentes de 2, 3 y 4 palabras ---

            from sklearn.feature_extraction.text import CountVectorizer

            st.subheader("🔁 Frases más repetidas en los verbatims (2, 3 y 4 palabras)")

            # Obtener solo los verbatims filtrados y limpios
            verbatims_validos = df_filtrado['💬 Verbatim de ejemplo'].dropna().astype(str).tolist()

            # Vectorizador para n-gramas
            vectorizer = CountVectorizer(ngram_range=(2, 4))
            X = vectorizer.fit_transform(verbatims_validos)

            # Calcular frecuencias
            frecuencias = pd.Series(X.toarray().sum(axis=0), index=vectorizer.get_feature_names_out())
            frecuencias = frecuencias.sort_values(ascending=False)

            # Eliminar conectores irrelevantes
            conectores = [
                "que me", "que no", "de la", "en la", "en el",
                "no se", "no me", "lo que", "con el", "todos los", "con la", "de los", "que se", 
                "con un", "es un", "para que", "en mi", "no es"
            ]
            frecuencias = frecuencias[~frecuencias.index.isin(conectores)]

            # Mostrar top N frases
            top_n = 30
            st.write(f"Mostrando las {top_n} frases más repetidas de 2 a 4 palabras:")
            st.dataframe(frecuencias.head(top_n).reset_index().rename(columns={"index": "Frase", 0: "Repeticiones"}))

            # Selección de una frase
            frase_seleccionada = st.selectbox("📌 Seleccioná una frase para ver verbatims que la contienen:", frecuencias.head(top_n).index.tolist())

            # Mostrar verbatims con esa frase + filtro por necesidad
            if frase_seleccionada:
                verbatims_con_frase = df_filtrado[df_filtrado['💬 Verbatim de ejemplo'].str.lower().str.contains(frase_seleccionada)]

                st.write(f"Se encontraron {len(verbatims_con_frase)} verbatims que contienen: '{frase_seleccionada}'")

                # Filtro por necesidad detectada
                if 'Necesidad Detectada' in verbatims_con_frase.columns:
                    necesidades = verbatims_con_frase['Necesidad Detectada'].unique().tolist()
                    necesidad_sel = st.selectbox("🎯 Filtrar por necesidad detectada:", ["Todas"] + necesidades)

                    if necesidad_sel != "Todas":
                        verbatims_con_frase = verbatims_con_frase[verbatims_con_frase['Necesidad Detectada'] == necesidad_sel]

                st.dataframe(verbatims_con_frase[['fecha', 'dni', '💬 Verbatim de ejemplo', 'Necesidad Detectada']])









