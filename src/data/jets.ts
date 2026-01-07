// Type definition for a jet aircraft
export interface Jet {
    model: string;
    manufacturer: string;
    type: string;
    yearStart: number;
    yearEnd: number;
    price: number;
    range: number;
    cruiseSpeed: number;
    passengers: number;
    totalHourlyCost?: number;
    multiYearTotalCost?: number;
    as?: number;
    ax?: number;
    ba?: number;
    bd?: number;
    bg?: number;
    bj?: number;
    [key: string]: string | number | undefined;
}

// Sample jet data - in a real implementation this would include more aircraft
export const jets: Jet[] = [
    {
        model: "Citation CJ4",
        manufacturer: "Cessna",
        type: "Light Jet",
        yearStart: 2010,
        yearEnd: 2023,
        price: 10500000,
        range: 2165,
        cruiseSpeed: 451,
        passengers: 9
    },
    {
        model: "Phenom 300",
        manufacturer: "Embraer",
        type: "Light Jet",
        yearStart: 2009,
        yearEnd: 2023,
        price: 9450000,
        range: 1971,
        cruiseSpeed: 453,
        passengers: 7
    },
    {
        model: "Challenger 350",
        manufacturer: "Bombardier",
        type: "Super Mid-Size Jet",
        yearStart: 2014,
        yearEnd: 2023,
        price: 26700000,
        range: 3200,
        cruiseSpeed: 470,
        passengers: 10
    }
];

/**
 * Calculate metrics for a jet based on user inputs
 * 
 * @param jet - The jet to calculate metrics for
 * @param yearsOfOwnership - Years of planned ownership
 * @param averageTripLength - Average trip length in hours
 * @param numberOfTrips - Number of trips per year
 * @param _ - Parameters below this are used in the App component but not here
 * @returns Jet with calculated metrics
 */
export function calculateJetMetrics(
    jet: Jet,
    yearsOfOwnership: number = 5,
    averageTripLength: number = 3,
    numberOfTrips: number = 24,
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    _1: number = 0,
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    _2: number = 0,
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    _3: number = 0,
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    _4: { lat: number; lng: number } | null = null,
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    _5: number = 0
): Jet {
    // Create a copy of the jet to avoid modifying the original
    const updatedJet = { ...jet };

    // Calculate hourly cost (simplified example)
    const baseCostPerHour = (jet.price * 0.00015) + (10 * jet.passengers);
    updatedJet.totalHourlyCost = baseCostPerHour;

    // Calculate multi-year total cost
    const annualCost = baseCostPerHour * averageTripLength * numberOfTrips;
    const depreciationRate = 0.05; // 5% annual depreciation
    const totalCost = (annualCost * yearsOfOwnership) + (jet.price * (1 - Math.pow(1 - depreciationRate, yearsOfOwnership)));
    updatedJet.multiYearTotalCost = totalCost;

    // Calculate scoring metrics
    updatedJet.as = 100 - (totalCost / 1000000); // Lower cost is better
    updatedJet.ax = (jet.range / 1000) * 25; // Range score
    updatedJet.ba = (jet.cruiseSpeed / 100) * 20; // Speed score
    updatedJet.bd = jet.passengers * 10; // Passenger capacity score
    updatedJet.bg = (jet.yearStart - 2000) * 2; // Newer is better

    // BJ score is a weighted average of all other scores
    updatedJet.bj = (
        updatedJet.as * 0.3 +
        updatedJet.ax * 0.2 +
        updatedJet.ba * 0.15 +
        updatedJet.bd * 0.15 +
        updatedJet.bg * 0.2
    );

    return updatedJet;
} 