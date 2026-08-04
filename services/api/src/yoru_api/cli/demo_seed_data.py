# ruff: noqa: E501
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class CategorySeed:
    code: str
    name: str
    description: str


@dataclass(frozen=True, slots=True)
class PartnerSeed:
    key: str
    display_name: str
    legal_name: str
    partner_type: str
    contact_email: str
    contact_phone: str
    address_line: str
    city: str
    province: str
    postal_code: str
    description: str


@dataclass(frozen=True, slots=True)
class ProductSeed:
    key: str
    partner_key: str
    category_code: str
    sku: str
    name: str
    slug: str
    description: str
    unit_price: Decimal
    stock: int
    reorder_level: int
    image_path: str
    alt_text: str


@dataclass(frozen=True, slots=True)
class ProfessionalSeed:
    key: str
    partner_key: str
    name: str
    title: str
    bio: str


@dataclass(frozen=True, slots=True)
class ServiceSeed:
    key: str
    partner_key: str
    category_code: str
    professional_keys: tuple[str, ...]
    name: str
    slug: str
    description: str
    duration_minutes: int
    price: Decimal
    capacity_per_slot: int


CATEGORIES = (
    CategorySeed("skincare", "Skincare", "Perawatan kulit terkurasi."),
    CategorySeed("hair-care", "Hair care", "Perawatan rambut dan kulit kepala."),
    CategorySeed("fashion", "Fashion", "Produk fashion dan aksesori."),
    CategorySeed("makeup", "Makeup", "Makeup dan colour cosmetics."),
    CategorySeed("facial-service", "Facial", "Layanan facial profesional di rumah."),
    CategorySeed("hair-service", "Hair", "Perawatan rambut profesional di rumah."),
    CategorySeed("grooming-service", "Grooming", "Grooming dan barber home visit."),
    CategorySeed("nail-service", "Nail", "Nail care dan manicure di rumah."),
    CategorySeed("styling-service", "Styling", "Personal styling untuk berbagai acara."),
)

PARTNERS = (
    PartnerSeed("luma", "Luma Skin Studio", "PT Luma Skin Indonesia", "merchant_service",
                "hello@luma.demo", "+62-811-1000-1001", "Jl. Senopati 18",
                "Jakarta Selatan", "DKI Jakarta", "12190",
                "Studio skincare dan home facial dengan pendekatan barrier-first."),
    PartnerSeed("atelier", "Atelier Hair Lab", "CV Atelier Hair Lab", "merchant_service",
                "hello@atelier.demo", "+62-811-1000-1002", "Jl. Riau 88",
                "Bandung", "Jawa Barat", "40115",
                "Hair care product dan home salon dengan protokol higienis."),
    PartnerSeed("nara", "Nara Objects", "CV Nara Objects", "merchant",
                "hello@nara.demo", "+62-811-1000-1003", "Jl. Kaliurang 21",
                "Yogyakarta", "DI Yogyakarta", "55281",
                "Everyday objects dengan desain minimal dan material terpilih."),
    PartnerSeed("serein", "Serein Lab", "PT Serein Lab Nusantara", "merchant",
                "hello@serein.demo", "+62-811-1000-1004", "Jl. Darmo 41",
                "Surabaya", "Jawa Timur", "60241",
                "Daily sun care untuk iklim tropis."),
    PartnerSeed("noir", "Noir Beauty", "PT Noir Beauty Indonesia", "merchant_service",
                "hello@noir.demo", "+62-811-1000-1005", "Alam Sutera Boulevard 12",
                "Tangerang", "Banten", "15325",
                "Colour cosmetics dan makeup artist home visit."),
    PartnerSeed("northside", "Northside Grooming", "CV Northside Grooming", "service",
                "hello@northside.demo", "+62-811-1000-1006", "Jl. Kemang Raya 55",
                "Jakarta Selatan", "DKI Jakarta", "12730",
                "Barber dan grooming profesional dengan layanan home visit."),
    PartnerSeed("mori", "Mori Nail Room", "CV Mori Nail Room", "service",
                "hello@mori.demo", "+62-811-1000-1007", "Jl. Cipete Raya 31",
                "Jakarta Selatan", "DKI Jakarta", "12410",
                "Nail care home service dengan alat steril dan warna terkurasi."),
    PartnerSeed("nara-styling", "Nara Styling", "CV Nara Styling", "service",
                "hello@narastyling.demo", "+62-811-1000-1008", "Jl. Cendana 9",
                "Sleman", "DI Yogyakarta", "55581",
                "Personal hijab styling untuk acara dan produksi konten."),
)

PRODUCTS = (
    ProductSeed("glow-reset", "luma", "skincare", "LUMA-GRS-20",
                "Glow Reset Serum", "glow-reset-serum",
                "Serum ringan untuk membantu merawat tampilan kulit kusam, menjaga hidrasi, dan memperkuat skin barrier.",
                Decimal("189000.00"), 42, 10, "/yoru-media/demo/product-serum.png",
                "Glow Reset Serum dalam botol dropper minimal."),
    ProductSeed("barrier-cloud", "luma", "skincare", "LUMA-BCM-50",
                "Barrier Cloud Moisturizer", "barrier-cloud-moisturizer",
                "Moisturizer cloud-gel yang nyaman, ringan, dan cocok untuk rutinitas barrier care.",
                Decimal("229000.00"), 31, 8, "/yoru-media/demo/product-moisturizer.png",
                "Barrier Cloud Moisturizer dalam jar."),
    ProductSeed("silk-repair", "atelier", "hair-care", "AHL-SRM-180",
                "Silk Repair Hair Mask", "silk-repair-hair-mask",
                "Masker rambut intensif untuk rambut kering dan sering di-styling.",
                Decimal("149000.00"), 55, 12, "/yoru-media/demo/product-hair-mask.png",
                "Silk Repair Hair Mask dalam jar."),
    ProductSeed("satin-tote", "nara", "fashion", "NARA-EST-INK",
                "Everyday Satin Tote", "everyday-satin-tote",
                "Tote berstruktur lembut dengan finishing satin matte untuk kerja dan agenda akhir pekan.",
                Decimal("279000.00"), 12, 4, "/yoru-media/demo/product-tote.png",
                "Everyday Satin Tote berwarna gelap."),
    ProductSeed("mineral-sun", "serein", "skincare", "SER-MSS-18",
                "Mineral Sun Stick SPF 50", "mineral-sun-stick",
                "Sun stick praktis untuk re-apply dengan hasil natural dan nyaman.",
                Decimal("139000.00"), 64, 15, "/yoru-media/demo/product-sunstick.png",
                "Mineral Sun Stick SPF 50."),
    ProductSeed("midnight-tint", "noir", "makeup", "NOIR-MLT-ROS",
                "Midnight Lip Tint", "midnight-lip-tint",
                "Lip tint buildable dengan soft-blur stain untuk aktivitas sehari-hari.",
                Decimal("99000.00"), 33, 10, "/yoru-media/demo/product-lip-tint.png",
                "Midnight Lip Tint warna After Rose."),
)

PROFESSIONALS = (
    ProfessionalSeed("nadia", "luma", "Nadia Rahma", "Senior aesthetician",
                     "Berpengalaman menangani home facial dan barrier consultation."),
    ProfessionalSeed("ayla", "luma", "Ayla Putri", "Skin therapist",
                     "Fokus pada gentle facial dan hydration care."),
    ProfessionalSeed("raka", "atelier", "Raka Pradana", "Hair therapist",
                     "Spesialis scalp care dan restorative hair treatment."),
    ProfessionalSeed("laras", "atelier", "Laras Wening", "Hair stylist",
                     "Hair stylist untuk natural finish dan event styling."),
    ProfessionalSeed("meira", "noir", "Meira Anjani", "Professional makeup artist",
                     "Makeup artist untuk wisuda, pesta, dan editorial look."),
    ProfessionalSeed("sasha", "noir", "Sasha Nirmala", "Beauty artist",
                     "Beauty artist dengan fokus complexion dan soft glam."),
    ProfessionalSeed("dimas", "northside", "Dimas Arga", "Senior barber",
                     "Barber home visit dengan fokus precision cut."),
    ProfessionalSeed("citra", "mori", "Citra Maharani", "Nail artist",
                     "Nail artist untuk manicure dan basic gel."),
    ProfessionalSeed("salsha", "nara-styling", "Salsha Kirana", "Hijab stylist",
                     "Personal hijab stylist untuk acara dan kebutuhan konten."),
)

SERVICES = (
    ServiceSeed("home-facial", "luma", "facial-service", ("nadia", "ayla"),
                "Home Facial Reset", "home-facial-reset",
                "Facial lengkap di rumah dengan konsultasi, gentle extraction, hydration, dan aftercare.",
                90, Decimal("349000.00"), 2),
    ServiceSeed("hair-spa", "atelier", "hair-service", ("raka", "laras"),
                "Hair Spa at Home", "hair-spa-home",
                "Perawatan rambut dan kulit kepala dengan pijat ringan dan natural blow dry.",
                75, Decimal("289000.00"), 2),
    ServiceSeed("event-makeup", "noir", "makeup", ("meira", "sasha"),
                "Event Makeup at Home", "makeup-event-home",
                "Makeup artist datang ke lokasi untuk wisuda, pesta, lamaran, atau acara formal.",
                120, Decimal("499000.00"), 2),
    ServiceSeed("men-grooming", "northside", "grooming-service", ("dimas",),
                "Men Grooming Home Visit", "men-grooming-home",
                "Haircut dan grooming profesional dengan peralatan steril di rumah.",
                60, Decimal("179000.00"), 1),
    ServiceSeed("nail-care", "mori", "nail-service", ("citra",),
                "Essential Nail Care", "nail-care-home",
                "Manicure dan basic gel polish di rumah dengan alat steril.",
                75, Decimal("229000.00"), 1),
    ServiceSeed("hijab-style", "nara-styling", "styling-service", ("salsha",),
                "Hijab Styling Home Visit", "hijab-styling-home",
                "Personal hijab styling untuk wisuda, lamaran, pesta, dan produksi konten.",
                60, Decimal("199000.00"), 1),
)
