export type AssetType = 'REAL_ESTATE' | 'STOCK' | 'PENSION' | 'SAVINGS' | 'PHYSICAL' | 'ETC'
export type Currency   = 'KRW' | 'USD' | 'JPY'

export interface HistoryItem {
  date:      string
  value?:    number
  price?:    number
  quantity?: number
}

export interface RealEstateDetail {
  isOwned:       boolean
  hasTenant:     boolean
  tenantDeposit: number
  address:       string
  loanAmount:    number
}

export interface StockDetail {
  accountName:      string
  currency:         Currency
  isPensionLike:    boolean
  pensionStartYear?: number
  pensionMonthly?:   number
  ticker?:           string
}

export interface PensionDetail {
  pensionType?:           string
  expectedStartYear:      number
  expectedEndYear:        number
  expectedMonthlyPayout:  number
  annualGrowthRate:       number
}

export interface SavingsDetail {
  isPensionLike:    boolean
  pensionStartYear?: number
  pensionMonthly?:   number
}

export type AssetDetail = RealEstateDetail | StockDetail | PensionDetail | SavingsDetail

export interface Asset {
  id:               string
  type:             AssetType
  name:             string
  currentValue:     number
  acquisitionDate:  string
  acquisitionPrice: number
  disposalDate?:    string
  disposalPrice?:   number
  quantity:         number
  createdAt:        string
  updatedAt:        string
  history:          HistoryItem[]
  detail?:          AssetDetail
}

export interface ChartDataPoint {
  date:   string
  label:  string
  value:  number
}

export interface ChartParams {
  type?:     AssetType
  period?:   'all' | '10y' | '3y' | '1y' | '3m' | '1m'
  group_by?: 'type' | 'name' | 'account'
  account?:  string
}

export interface CategoryKpi {
  totalAsset:     number
  totalLiability: number
  netWorth:       number
}

export interface Settings {
  currentAge:    number
  retirementAge: number
  [key: string]: number | string
}
