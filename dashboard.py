"""
Dashboard interativo da Copa do Mundo FIFA (1930 - 2014).

Execução:
    streamlit run dashboard.py
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# Configuração da página
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Dashboard Copa do Mundo FIFA",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_DIR = Path(__file__).parent / "data"


# ---------------------------------------------------------------------------
# Carregamento e tratamento dos dados
# ---------------------------------------------------------------------------
@st.cache_data
def load_world_cups() -> pd.DataFrame:
    """Carrega a tabela geral das Copas do Mundo."""
    df = pd.read_csv(DATA_DIR / "WorldCups.csv")

    # "Attendance" vem com ponto como separador de milhar (ex.: "3.178.856").
    df["Attendance"] = (
        df["Attendance"].astype(str).str.replace(".", "", regex=False).astype(float)
    )

    # Unifica "Germany FR" (República Federal da Alemanha) com "Germany".
    text_cols = ["Winner", "Runners-Up", "Third", "Fourth"]
    for col in text_cols:
        df[col] = df[col].str.strip().replace({"Germany FR": "Germany"})

    df["Year"] = df["Year"].astype(int)
    return df


@st.cache_data
def load_matches() -> pd.DataFrame:
    """Carrega e limpa as partidas de todas as Copas."""
    df = pd.read_csv(DATA_DIR / "WorldCupMatches.csv")

    # O CSV traz linhas completamente vazias ao final — removemos.
    df = df.dropna(subset=["Year", "Home Team Name", "Away Team Name"])
    df["Year"] = df["Year"].astype(int)

    # Normaliza nomes de times (remove espaços e unifica Alemanha).
    for col in ["Home Team Name", "Away Team Name", "Stadium", "City", "Stage"]:
        df[col] = df[col].astype(str).str.strip()

    df["Home Team Name"] = df["Home Team Name"].replace({"Germany FR": "Germany"})
    df["Away Team Name"] = df["Away Team Name"].replace({"Germany FR": "Germany"})

    df["Home Team Goals"] = df["Home Team Goals"].astype(int)
    df["Away Team Goals"] = df["Away Team Goals"].astype(int)
    df["Total Goals"] = df["Home Team Goals"] + df["Away Team Goals"]

    # Resultado do ponto de vista do mandante.
    df["Result"] = df.apply(
        lambda r: (
            "Vitória mandante"
            if r["Home Team Goals"] > r["Away Team Goals"]
            else "Vitória visitante"
            if r["Home Team Goals"] < r["Away Team Goals"]
            else "Empate"
        ),
        axis=1,
    )

    return df


@st.cache_data
def load_players() -> pd.DataFrame:
    """Carrega os dados de jogadores."""
    df = pd.read_csv(DATA_DIR / "WorldCupPlayers.csv")
    df["Player Name"] = df["Player Name"].astype(str).str.strip()
    df["Team Initials"] = df["Team Initials"].astype(str).str.strip()
    df["Event"] = df["Event"].fillna("")
    return df


def build_team_goals_table(matches: pd.DataFrame) -> pd.DataFrame:
    """Agrega gols marcados e sofridos por seleção."""
    home = matches.groupby("Home Team Name").agg(
        goals_scored=("Home Team Goals", "sum"),
        goals_conceded=("Away Team Goals", "sum"),
        matches=("MatchID", "count"),
    )
    away = matches.groupby("Away Team Name").agg(
        goals_scored=("Away Team Goals", "sum"),
        goals_conceded=("Home Team Goals", "sum"),
        matches=("MatchID", "count"),
    )
    total = home.add(away, fill_value=0).reset_index()
    total = total.rename(columns={"index": "Team"})
    total.columns = ["Team", "Gols sofridos", "Partidas", "Gols marcados"]
    total = total[["Team", "Partidas", "Gols marcados", "Gols sofridos"]]
    total["Saldo"] = total["Gols marcados"] - total["Gols sofridos"]
    total = total.sort_values("Gols marcados", ascending=False)
    return total


# ---------------------------------------------------------------------------
# Dados carregados
# ---------------------------------------------------------------------------
world_cups = load_world_cups()
matches = load_matches()
players = load_players()


# ---------------------------------------------------------------------------
# Sidebar — filtros
# ---------------------------------------------------------------------------
st.sidebar.title("⚽ Filtros")

year_min, year_max = int(world_cups["Year"].min()), int(world_cups["Year"].max())
year_range = st.sidebar.slider(
    "Intervalo de anos",
    min_value=year_min,
    max_value=year_max,
    value=(year_min, year_max),
    step=4,
)

all_winners = sorted(world_cups["Winner"].unique())
selected_winners = st.sidebar.multiselect(
    "Selecionar campeões (opcional)",
    options=all_winners,
    default=[],
    help="Deixe vazio para considerar todos os campeões.",
)

st.sidebar.markdown("---")
st.sidebar.caption(
    "Fonte: [FIFA World Cup Dataset (Kaggle)]"
    "(https://www.kaggle.com/datasets/abecklas/fifa-world-cup)"
)

# Aplicação dos filtros
mask_years = world_cups["Year"].between(year_range[0], year_range[1])
wc_filtered = world_cups[mask_years].copy()
if selected_winners:
    wc_filtered = wc_filtered[wc_filtered["Winner"].isin(selected_winners)]

matches_filtered = matches[matches["Year"].between(year_range[0], year_range[1])].copy()


# ---------------------------------------------------------------------------
# Cabeçalho
# ---------------------------------------------------------------------------
st.title("🏆 Dashboard Copa do Mundo FIFA")
st.markdown(
    f"Análise das Copas do Mundo entre **{year_range[0]}** e **{year_range[1]}** — "
    "utilize o menu lateral para refinar os filtros."
)

if wc_filtered.empty:
    st.warning("Nenhuma Copa do Mundo corresponde aos filtros selecionados.")
    st.stop()


# ---------------------------------------------------------------------------
# KPIs
# ---------------------------------------------------------------------------
total_cups = len(wc_filtered)
total_goals = int(wc_filtered["GoalsScored"].sum())
total_matches = int(wc_filtered["MatchesPlayed"].sum())
total_attendance = int(wc_filtered["Attendance"].sum())
avg_goals_per_match = total_goals / total_matches if total_matches else 0
top_winner = (
    wc_filtered["Winner"].value_counts().idxmax() if not wc_filtered.empty else "-"
)
top_winner_count = (
    int(wc_filtered["Winner"].value_counts().max()) if not wc_filtered.empty else 0
)

kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)
kpi1.metric("Copas analisadas", f"{total_cups}")
kpi2.metric("Gols marcados", f"{total_goals:,}".replace(",", "."))
kpi3.metric("Partidas disputadas", f"{total_matches:,}".replace(",", "."))
kpi4.metric("Média gols/partida", f"{avg_goals_per_match:.2f}")
kpi5.metric(
    "Público total",
    f"{total_attendance:,}".replace(",", "."),
    help="Somatório do público nas Copas do filtro.",
)
kpi6.metric("Maior campeão", top_winner, f"{top_winner_count} título(s)")

st.markdown("---")


# ---------------------------------------------------------------------------
# Abas
# ---------------------------------------------------------------------------
tab_overview, tab_teams, tab_matches, tab_players, tab_data = st.tabs(
    ["📊 Visão geral", "🌍 Seleções", "⚽ Partidas", "👤 Jogadores", "🗃️ Dados"]
)


# ---------------------------------------------------------------------------
# Aba 1 — Visão geral
# ---------------------------------------------------------------------------
with tab_overview:
    col1, col2 = st.columns(2)

    with col1:
        fig_goals = px.line(
            wc_filtered,
            x="Year",
            y="GoalsScored",
            markers=True,
            title="Gols marcados por edição",
            labels={"GoalsScored": "Gols", "Year": "Ano"},
        )
        fig_goals.update_traces(line_color="#1f77b4", line_width=3)
        fig_goals.update_layout(hovermode="x unified")
        st.plotly_chart(fig_goals, width="stretch")

    with col2:
        fig_att = px.bar(
            wc_filtered,
            x="Year",
            y="Attendance",
            title="Público total por edição",
            labels={"Attendance": "Público", "Year": "Ano"},
            color="Attendance",
            color_continuous_scale="Viridis",
        )
        fig_att.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig_att, width="stretch")

    col3, col4 = st.columns(2)

    with col3:
        wc_filtered["GoalsPerMatch"] = (
            wc_filtered["GoalsScored"] / wc_filtered["MatchesPlayed"]
        )
        fig_ratio = px.line(
            wc_filtered,
            x="Year",
            y="GoalsPerMatch",
            markers=True,
            title="Média de gols por partida",
            labels={"GoalsPerMatch": "Gols/partida", "Year": "Ano"},
        )
        fig_ratio.update_traces(line_color="#d62728", line_width=3)
        st.plotly_chart(fig_ratio, width="stretch")

    with col4:
        fig_teams = px.bar(
            wc_filtered,
            x="Year",
            y="QualifiedTeams",
            title="Seleções participantes",
            labels={"QualifiedTeams": "Seleções", "Year": "Ano"},
            color="QualifiedTeams",
            color_continuous_scale="Blues",
        )
        fig_teams.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig_teams, width="stretch")


# ---------------------------------------------------------------------------
# Aba 2 — Seleções
# ---------------------------------------------------------------------------
with tab_teams:
    col1, col2 = st.columns([1, 1])

    with col1:
        champions = (
            wc_filtered["Winner"].value_counts().reset_index()
        )
        champions.columns = ["Seleção", "Títulos"]
        fig_champ = px.bar(
            champions,
            x="Títulos",
            y="Seleção",
            orientation="h",
            title="Títulos por seleção",
            color="Títulos",
            color_continuous_scale="OrRd",
            text="Títulos",
        )
        fig_champ.update_layout(
            yaxis={"categoryorder": "total ascending"},
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig_champ, width="stretch")

    with col2:
        podium_cols = ["Winner", "Runners-Up", "Third", "Fourth"]
        podium = (
            wc_filtered[podium_cols]
            .melt(var_name="Posição", value_name="Seleção")
            .groupby(["Seleção", "Posição"])
            .size()
            .reset_index(name="Qtd")
        )
        order = {"Winner": 1, "Runners-Up": 2, "Third": 3, "Fourth": 4}
        podium["ord"] = podium["Posição"].map(order)
        podium = podium.sort_values("ord")

        top_teams = (
            podium.groupby("Seleção")["Qtd"].sum().sort_values(ascending=False).head(12)
        ).index
        podium_top = podium[podium["Seleção"].isin(top_teams)]

        fig_podium = px.bar(
            podium_top,
            x="Seleção",
            y="Qtd",
            color="Posição",
            title="Presenças no pódio (top 12)",
            category_orders={"Posição": ["Winner", "Runners-Up", "Third", "Fourth"]},
            color_discrete_map={
                "Winner": "#FFD700",
                "Runners-Up": "#C0C0C0",
                "Third": "#CD7F32",
                "Fourth": "#6c757d",
            },
        )
        fig_podium.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig_podium, width="stretch")

    st.subheader("Desempenho geral das seleções")
    team_stats = build_team_goals_table(matches_filtered)
    top_n = st.slider("Mostrar top N seleções", 5, 30, 15)

    fig_scored = px.bar(
        team_stats.head(top_n),
        x="Gols marcados",
        y="Team",
        orientation="h",
        title=f"Top {top_n} seleções em gols marcados",
        color="Gols marcados",
        color_continuous_scale="Greens",
    )
    fig_scored.update_layout(
        yaxis={"categoryorder": "total ascending"},
        coloraxis_showscale=False,
    )
    st.plotly_chart(fig_scored, width="stretch")

    st.dataframe(team_stats.reset_index(drop=True), width="stretch")


# ---------------------------------------------------------------------------
# Aba 3 — Partidas
# ---------------------------------------------------------------------------
with tab_matches:
    col1, col2 = st.columns(2)

    with col1:
        results_counts = matches_filtered["Result"].value_counts().reset_index()
        results_counts.columns = ["Resultado", "Partidas"]
        fig_results = px.pie(
            results_counts,
            values="Partidas",
            names="Resultado",
            title="Distribuição de resultados (mandante vs visitante)",
            hole=0.45,
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        st.plotly_chart(fig_results, width="stretch")

    with col2:
        stage_goals = (
            matches_filtered.groupby("Stage")["Total Goals"]
            .sum()
            .sort_values(ascending=False)
            .head(15)
            .reset_index()
        )
        fig_stage = px.bar(
            stage_goals,
            x="Total Goals",
            y="Stage",
            orientation="h",
            title="Gols por fase da competição (top 15)",
            color="Total Goals",
            color_continuous_scale="Purples",
        )
        fig_stage.update_layout(
            yaxis={"categoryorder": "total ascending"},
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig_stage, width="stretch")

    st.subheader("Maiores goleadas")
    biggest = matches_filtered.copy()
    biggest["Diferença"] = (
        biggest["Home Team Goals"] - biggest["Away Team Goals"]
    ).abs()
    biggest = biggest.nlargest(15, "Diferença")[
        [
            "Year",
            "Stage",
            "Home Team Name",
            "Home Team Goals",
            "Away Team Goals",
            "Away Team Name",
            "City",
            "Stadium",
        ]
    ].rename(
        columns={
            "Year": "Ano",
            "Stage": "Fase",
            "Home Team Name": "Mandante",
            "Home Team Goals": "Gols M.",
            "Away Team Goals": "Gols V.",
            "Away Team Name": "Visitante",
            "City": "Cidade",
            "Stadium": "Estádio",
        }
    )
    st.dataframe(biggest.reset_index(drop=True), width="stretch")

    st.subheader("Gols por Copa — distribuição por fase")
    heat = (
        matches_filtered.groupby(["Year", "Stage"])["Total Goals"].sum().reset_index()
    )
    fig_heat = px.density_heatmap(
        heat,
        x="Year",
        y="Stage",
        z="Total Goals",
        color_continuous_scale="YlOrRd",
        title="Gols por edição e fase",
    )
    st.plotly_chart(fig_heat, width="stretch")


# ---------------------------------------------------------------------------
# Aba 4 — Jogadores
# ---------------------------------------------------------------------------
with tab_players:
    # Filtra jogadores pelas partidas dentro do intervalo selecionado.
    match_ids = matches_filtered["MatchID"].unique()
    players_filtered = players[players["MatchID"].isin(match_ids)].copy()

    # Extrai gols do campo "Event" (G + minuto).
    players_filtered["Gols"] = (
        players_filtered["Event"].str.count(r"G\d+")
    ).fillna(0).astype(int)

    top_scorers = (
        players_filtered.groupby(["Player Name", "Team Initials"])["Gols"]
        .sum()
        .reset_index()
        .sort_values("Gols", ascending=False)
    )
    top_scorers = top_scorers[top_scorers["Gols"] > 0].head(20)

    col1, col2 = st.columns([2, 1])

    with col1:
        fig_top = px.bar(
            top_scorers,
            x="Gols",
            y="Player Name",
            orientation="h",
            color="Gols",
            color_continuous_scale="Reds",
            title="Top 20 artilheiros (no intervalo filtrado)",
            hover_data=["Team Initials"],
        )
        fig_top.update_layout(
            yaxis={"categoryorder": "total ascending"},
            coloraxis_showscale=False,
            height=600,
        )
        st.plotly_chart(fig_top, width="stretch")

    with col2:
        total_players = players_filtered["Player Name"].nunique()
        total_goals_players = int(players_filtered["Gols"].sum())
        total_teams_players = players_filtered["Team Initials"].nunique()

        st.metric("Jogadores únicos", f"{total_players:,}".replace(",", "."))
        st.metric("Gols registrados", f"{total_goals_players:,}".replace(",", "."))
        st.metric("Seleções", f"{total_teams_players}")

        st.caption(
            "Os gols são extraídos do campo `Event` (padrão `G<minuto>`). "
            "Gols contra (`OG`) não são contabilizados."
        )

    st.subheader("Tabela de artilheiros")
    st.dataframe(
        top_scorers.rename(
            columns={"Player Name": "Jogador", "Team Initials": "Seleção"}
        ).reset_index(drop=True),
        width="stretch",
    )


# ---------------------------------------------------------------------------
# Aba 5 — Dados brutos
# ---------------------------------------------------------------------------
with tab_data:
    st.subheader("Copas do Mundo")
    st.dataframe(wc_filtered.reset_index(drop=True), width="stretch")

    st.subheader("Partidas")
    st.dataframe(
        matches_filtered.drop(columns=["Result"]).reset_index(drop=True),
        width="stretch",
        height=320,
    )

    st.download_button(
        "⬇️ Baixar partidas filtradas (CSV)",
        data=matches_filtered.to_csv(index=False).encode("utf-8"),
        file_name=f"partidas_{year_range[0]}_{year_range[1]}.csv",
        mime="text/csv",
    )
