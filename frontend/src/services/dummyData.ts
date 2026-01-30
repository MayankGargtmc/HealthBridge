/**
 * Demo Data for Health Surveillance Dashboard
 * Contains ~3000 patient sample data for demonstration purposes.
 * 
 * To use real data instead, remove ?demo=true from the URL
 */

export const dummyDashboardData = {
  documents: {
    total: 3245,
    processed: 3156,
    pending: 67,
    failed: 22,
  },
  patients: {
    total: 3000,
    with_contact: 2847,
  },
  diseases: {
    unique_diseases: 24,
    total_diagnoses: 4521,
  },
  gender_distribution: [
    { gender: "male", count: 1567 },
    { gender: "female", count: 1389 },
    { gender: "other", count: 44 },
  ],
  top_diseases: [
    { id: "demo-1", name: "Hypertension", patient_count: 640 },
    { id: "demo-2", name: "Diabetes Mellitus Type 2", patient_count: 624 },
    { id: "demo-3", name: "Dengue Fever", patient_count: 403 },
    { id: "demo-4", name: "Coronary Artery Disease", patient_count: 375 },
    { id: "demo-5", name: "Urinary Tract Infection", patient_count: 318 },
    { id: "demo-6", name: "COPD", patient_count: 265 },
    { id: "demo-7", name: "Influenza", patient_count: 234 },
    { id: "demo-8", name: "Chickenpox", patient_count: 185 },
    { id: "demo-9", name: "Acute Gastroenteritis", patient_count: 167 },
    { id: "demo-10", name: "Typhoid", patient_count: 145 },
  ],
  recent_documents: [
    { id: "doc-1", original_filename: "lab_report_2026_01_30.pdf", processing_status: "completed", created_at: "2026-01-30T14:23:00Z" },
    { id: "doc-2", original_filename: "prescription_batch_456.pdf", processing_status: "completed", created_at: "2026-01-30T13:45:00Z" },
    { id: "doc-3", original_filename: "clinical_notes_789.pdf", processing_status: "processing", created_at: "2026-01-30T13:12:00Z" },
    { id: "doc-4", original_filename: "discharge_summary.pdf", processing_status: "completed", created_at: "2026-01-30T12:34:00Z" },
    { id: "doc-5", original_filename: "radiology_report.pdf", processing_status: "completed", created_at: "2026-01-30T11:56:00Z" },
  ],
}

export const dummySurveillanceData = {
  alerts: [
    {
      disease: "Dengue Fever",
      disease_id: "demo-dengue-fever",
      severity: "critical" as const,
      recent_cases: 156,
      baseline_avg: 45.2,
      increase_ratio: 3.45,
      message: "Dengue outbreak detected - 245% above normal levels",
    },
    {
      disease: "Influenza",
      disease_id: "demo-influenza",
      severity: "critical" as const,
      recent_cases: 234,
      baseline_avg: 120.5,
      increase_ratio: 1.94,
      message: "Seasonal flu surge - 94% above baseline",
    },
    {
      disease: "Acute Gastroenteritis",
      disease_id: "demo-gastro",
      severity: "warning" as const,
      recent_cases: 89,
      baseline_avg: 62.3,
      increase_ratio: 1.43,
      message: "Gastroenteritis cases elevated - 43% increase",
    },
    {
      disease: "Typhoid",
      disease_id: "demo-typhoid",
      severity: "warning" as const,
      recent_cases: 34,
      baseline_avg: 24.1,
      increase_ratio: 1.41,
      message: "Typhoid cases rising in eastern regions",
    },
    {
      disease: "Pneumonia",
      disease_id: "demo-pneumonia",
      severity: "warning" as const,
      recent_cases: 67,
      baseline_avg: 48.5,
      increase_ratio: 1.38,
      message: "Pneumonia cases above seasonal average",
    },
    {
      disease: "Malaria",
      disease_id: "demo-malaria",
      severity: "warning" as const,
      recent_cases: 45,
      baseline_avg: 35.0,
      increase_ratio: 1.29,
      message: "Malaria cases increasing post-monsoon",
    },
  ],
  geographic_clusters: [
    {
      type: "location",
      location: "Mumbai, Maharashtra",
      patient_count: 487,
      disease_count: 12,
      top_diseases: [
        { name: "Dengue Fever", count: 89 },
        { name: "Hypertension", count: 67 },
        { name: "Diabetes Mellitus Type 2", count: 54 },
      ],
    },
    {
      type: "location",
      location: "Delhi, Delhi",
      patient_count: 423,
      disease_count: 11,
      top_diseases: [
        { name: "Influenza", count: 112 },
        { name: "Pneumonia", count: 45 },
        { name: "Acute Bronchitis", count: 38 },
      ],
    },
    {
      type: "location",
      location: "Bangalore, Karnataka",
      patient_count: 356,
      disease_count: 10,
      top_diseases: [
        { name: "Dengue Fever", count: 67 },
        { name: "COVID-19", count: 34 },
        { name: "Typhoid", count: 28 },
      ],
    },
    {
      type: "location",
      location: "Chennai, Tamil Nadu",
      patient_count: 289,
      disease_count: 9,
      top_diseases: [
        { name: "Malaria", count: 45 },
        { name: "Dengue Fever", count: 42 },
        { name: "Acute Gastroenteritis", count: 35 },
      ],
    },
    {
      type: "location",
      location: "Kolkata, West Bengal",
      patient_count: 267,
      disease_count: 8,
      top_diseases: [
        { name: "Typhoid", count: 52 },
        { name: "Hepatitis A", count: 28 },
        { name: "Acute Gastroenteritis", count: 34 },
      ],
    },
    {
      type: "location",
      location: "Hyderabad, Telangana",
      patient_count: 234,
      disease_count: 8,
      top_diseases: [
        { name: "Dengue Fever", count: 38 },
        { name: "Chikungunya", count: 25 },
        { name: "Malaria", count: 22 },
      ],
    },
    {
      type: "location",
      location: "Pune, Maharashtra",
      patient_count: 198,
      disease_count: 7,
      top_diseases: [
        { name: "Influenza", count: 34 },
        { name: "Dengue Fever", count: 28 },
        { name: "Hypertension", count: 45 },
      ],
    },
    {
      type: "location",
      location: "Ahmedabad, Gujarat",
      patient_count: 167,
      disease_count: 6,
      top_diseases: [
        { name: "Acute Gastroenteritis", count: 42 },
        { name: "Typhoid", count: 23 },
        { name: "Diabetes Mellitus Type 2", count: 35 },
      ],
    },
  ],
  age_concentrations: [
    {
      disease: "Chickenpox",
      disease_id: "demo-chickenpox",
      dominant_age_group: "0-17",
      concentration: 78.5,
      patient_count: 145,
      total_patients: 185,
      description: "Chickenpox primarily affects Pediatric population",
    },
    {
      disease: "Hand Foot Mouth Disease",
      disease_id: "demo-hfmd",
      dominant_age_group: "0-17",
      concentration: 92.3,
      patient_count: 72,
      total_patients: 78,
      description: "Hand Foot Mouth Disease primarily affects Pediatric population",
    },
    {
      disease: "Coronary Artery Disease",
      disease_id: "demo-cad",
      dominant_age_group: "60+",
      concentration: 62.4,
      patient_count: 234,
      total_patients: 375,
      description: "Coronary Artery Disease primarily affects Elderly population",
    },
    {
      disease: "Hypertension",
      disease_id: "demo-hypertension",
      dominant_age_group: "45-59",
      concentration: 45.2,
      patient_count: 289,
      total_patients: 640,
      description: "Hypertension primarily affects Middle Age population",
    },
    {
      disease: "Diabetes Mellitus Type 2",
      disease_id: "demo-diabetes",
      dominant_age_group: "45-59",
      concentration: 42.8,
      patient_count: 267,
      total_patients: 624,
      description: "Diabetes Mellitus Type 2 primarily affects Middle Age population",
    },
    {
      disease: "Dengue Fever",
      disease_id: "demo-dengue",
      dominant_age_group: "18-29",
      concentration: 38.7,
      patient_count: 156,
      total_patients: 403,
      description: "Dengue Fever primarily affects Young Adult population",
    },
    {
      disease: "COPD",
      disease_id: "demo-copd",
      dominant_age_group: "60+",
      concentration: 71.2,
      patient_count: 189,
      total_patients: 265,
      description: "COPD primarily affects Elderly population",
    },
    {
      disease: "Urinary Tract Infection",
      disease_id: "demo-uti",
      dominant_age_group: "18-29",
      concentration: 42.1,
      patient_count: 134,
      total_patients: 318,
      description: "Urinary Tract Infection primarily affects Young Adult population",
    },
  ],
}

// Generate daily trends data
const generateTrendsData = (days: number) => {
  const diseases = ["Dengue Fever", "Influenza", "Hypertension", "Diabetes Mellitus Type 2", "Acute Gastroenteritis", "Typhoid", "Malaria", "Pneumonia"]
  const baseCounts: Record<string, number> = {
    "Dengue Fever": 15,
    "Influenza": 25,
    "Hypertension": 18,
    "Diabetes Mellitus Type 2": 16,
    "Acute Gastroenteritis": 8,
    "Typhoid": 4,
    "Malaria": 5,
    "Pneumonia": 7,
  }
  
  const daily_trends: Record<string, Array<{ date: string; count: number }>> = {}
  
  diseases.forEach((disease) => {
    daily_trends[disease] = []
    const base = baseCounts[disease] || 10
    
    for (let i = 0; i < days; i++) {
      const date = new Date()
      date.setDate(date.getDate() - (days - i - 1))
      
      // Add variation and trend
      const variation = Math.random() * base * 0.6 - base * 0.3
      let trend = 0
      if (disease === "Dengue Fever") trend = i * 0.5
      else if (disease === "Influenza") trend = i * 0.3
      
      const count = Math.max(0, Math.round(base + variation + trend))
      daily_trends[disease].push({
        date: date.toISOString().split('T')[0],
        count
      })
    }
  })
  
  return {
    period_days: days,
    daily_trends,
    weekly_trends: []
  }
}

export const dummyTrendsData = generateTrendsData(30)

export const dummyComorbidityData = {
  comorbidities: [
    { disease_1: "Diabetes Mellitus Type 2", disease_2: "Hypertension", co_occurrence_count: 312 },
    { disease_1: "Hypertension", disease_2: "Coronary Artery Disease", co_occurrence_count: 187 },
    { disease_1: "Diabetes Mellitus Type 2", disease_2: "Chronic Kidney Disease", co_occurrence_count: 134 },
    { disease_1: "Diabetes Mellitus Type 2", disease_2: "Coronary Artery Disease", co_occurrence_count: 156 },
    { disease_1: "COPD", disease_2: "Coronary Artery Disease", co_occurrence_count: 98 },
    { disease_1: "Hypertension", disease_2: "Chronic Kidney Disease", co_occurrence_count: 89 },
    { disease_1: "Asthma", disease_2: "Acute Bronchitis", co_occurrence_count: 76 },
    { disease_1: "Hypothyroidism", disease_2: "Hypertension", co_occurrence_count: 67 },
    { disease_1: "Arthritis", disease_2: "Hypertension", co_occurrence_count: 54 },
    { disease_1: "Diabetes Mellitus Type 2", disease_2: "Hypothyroidism", co_occurrence_count: 45 },
    { disease_1: "Hypertension", disease_2: "Hypothyroidism", co_occurrence_count: 42 },
    { disease_1: "Diabetes Mellitus Type 2", disease_2: "Arthritis", co_occurrence_count: 38 },
  ],
  total_analyzed: 1847,
}
