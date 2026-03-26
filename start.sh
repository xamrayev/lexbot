#!/bin/bash

# ==============================================
# Quick Start Script for llm-graph-builder
# O'zbekiston Mehnat Kodeksi
# ==============================================

set -e

echo "🚀 llm-graph-builder — Ishga Tushirish"
echo "======================================="

# Ranglar
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Papkaga o'tish
cd "$(dirname "$0")"

echo -e "${BLUE}1. Ma'lumotlar faylini tekshirish...${NC}"
if [ ! -f "data/mehnat_kodeksi_processed.json" ]; then
    echo -e "${RED}❌ Xatolik: data/mehnat_kodeksi_processed.json fayli topilmadi!${NC}"
    echo "Faylni quyidagi manzildan ko'chiring:"
    echo "  cp ../data/mehnat_kodeksi_processed.json data/"
    exit 1
fi
echo -e "${GREEN}✅ Ma'lumotlar fayli topildi${NC}"

echo -e "${BLUE}2. .env faylini tekshirish...${NC}"
if [ ! -f "backend/.env" ]; then
    echo -e "${RED}❌ Xatolik: backend/.env fayli topilmadi!${NC}"
    exit 1
fi
echo -e "${GREEN}✅ .env fayli topildi${NC}"

echo -e "${BLUE}3. Docker versiyasini tekshirish...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker o'rnatilmagan!${NC}"
    echo "Docker Desktop ni o'rnating: https://www.docker.com/products/docker-desktop"
    exit 1
fi
echo -e "${GREEN}✅ Docker versiyasi: $(docker --version)${NC}"

echo -e "${BLUE}4. Docker Compose versiyasini tekshirish...${NC}"
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose o'rnatilmagan!${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Docker Compose versiyasi: $(docker-compose --version)${NC}"

echo -e "${BLUE}5. Neo4j konteynerini ishga tushirish...${NC}"
docker-compose -f docker-compose-uzbek.yml up -d neo4j

echo -e "${BLUE}6. Neo4j tayyor bo'lishini kutish (30 soniya)...${NC}"
sleep 30

echo -e "${BLUE}7. Backend va Frontend ni ishga tushirish...${NC}"
docker-compose -f docker-compose-uzbek.yml up -d backend frontend

echo -e "${BLUE}8. Barcha xizmatlarni tekshirish...${NC}"
sleep 10
docker-compose -f docker-compose-uzbek.yml ps

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}✅ Tayyor! Barcha xizmatlar ishga tushdi.${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "📌 Foydalanish:"
echo "   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   🌐 UI Interface:     http://localhost:8080"
echo "   🗄️  Neo4j Browser:    http://localhost:7474"
echo "   📚 API Docs:         http://localhost:8000/docs"
echo "   ✅ Health Check:     http://localhost:8000/health"
echo ""
echo "🔑 Neo4j Login:"
echo "   Username: neo4j"
echo "   Password: LegalGraph2024!"
echo ""
echo "📝 Keyingi qadamlar:"
echo "   1. http://localhost:8080 ga o'ting"
echo "   2. 'Upload' bo'limiga kiring"
echo "   3. mehnat_kodeksi_processed.json faylini yuklang"
echo "   4. 'Build Graph' tugmasini bosing"
echo "   5. Graf yaratilishini kuting (5-10 daqiqa)"
echo ""
echo "🛑 To'xtatish:"
echo "   docker-compose -f docker-compose-uzbek.yml down"
echo ""
echo "📊 Loglarni ko'rish:"
echo "   docker-compose -f docker-compose-uzbek.yml logs -f backend"
echo ""
