import { useState, useMemo, useRef, useEffect, useCallback } from 'react'
// eslint-disable-next-line @typescript-eslint/ban-ts-comment
// @ts-ignore
import { jets, Jet, calculateJetMetrics } from './data/jets'
import jetschoolLogo from './assets/jetschool-logo.svg'
import 'rc-slider/assets/index.css'

// Reference the Google Maps types from the installed package
// No need to declare the modules as they're provided by @types/google.maps
declare global {
  interface Window {
    google: typeof google;
  }
}

interface Filters {
  range: number;
  passengers: number;
  averagePrice: number;
  lowestYearModel: number;
  yearsOfOwnership: number;
  averageTripLength: number;
  numberOfTrips: number;
  charterTripLength: number;
  numberOfCharterTrips: number;
  charterProfitPercentage: number;
  plannedPassengers: number;
  passengerPay: number;
  userLocation: {
    lat: number;
    lng: number;
  } | null;
  rangeCircleRadius: number;
}

const steps = [
  {
    title: "Basic Requirements",
    fields: ["lowestYearModel", "passengers", "averagePrice"],
    description: "Let's start with your basic aircraft requirements"
  },
  {
    title: "Range Requirements",
    fields: ["range", "rangeCircleRadius"],
    description: "Define your range requirements and location",
    hasMap: true
  },
  {
    title: "Ownership Details",
    fields: ["yearsOfOwnership", "averageTripLength", "numberOfTrips"],
    description: "Tell us about your planned usage"
  },
  {
    title: "Charter Information",
    fields: ["charterTripLength", "numberOfCharterTrips", "charterProfitPercentage"],
    description: "If you plan to charter your aircraft"
  },
  {
    title: "Passenger Details",
    fields: ["plannedPassengers", "passengerPay"],
    description: "Additional passenger information"
  }
];

const fieldLabels: Record<string, string> = {
  range: "Required Range (nautical miles)",
  rangeCircleRadius: "Range Circle Radius (nautical miles)",
  passengers: "Minimum Passengers",
  averagePrice: "Maximum Price ($)",
  lowestYearModel: "Minimum Year Model",
  yearsOfOwnership: "Planned Years of Ownership",
  averageTripLength: "Average Trip Length (hours)",
  numberOfTrips: "Number of Trips per Year",
  charterTripLength: "Average Charter Trip Length (hours)",
  numberOfCharterTrips: "Number of Charter Trips per Year",
  charterProfitPercentage: "Charter Profit Percentage (%)",
  plannedPassengers: "Typical Number of Passengers",
  passengerPay: "Passenger Pay per Trip ($)"
};

// Define the columns that can be filtered
interface ColumnFilter {
  column: string;
  operator: 'eq' | 'gt' | 'lt' | 'gte' | 'lte' | 'contains';
  value: string | number;
}

// Define the ranking columns
const rankingColumns = [
  { key: 'as', label: 'AS Score' },
  { key: 'ax', label: 'AX Score' },
  { key: 'ba', label: 'BA Score' },
  { key: 'bd', label: 'BD Score' },
  { key: 'bg', label: 'BG Score' },
  { key: 'bj', label: 'BJ Score' }
];

function App() {
  const [currentStep, setCurrentStep] = useState(0);
  const [showResults, setShowResults] = useState(false);
  const [selectedJets, setSelectedJets] = useState<Jet[]>([]);
  const [showComparison, setShowComparison] = useState(false);
  const [filters, setFilters] = useState<Filters>({
    range: 0,
    passengers: 0,
    averagePrice: 0,
    lowestYearModel: 1970,
    yearsOfOwnership: 5,
    averageTripLength: 0,
    numberOfTrips: 0,
    charterTripLength: 0,
    numberOfCharterTrips: 0,
    charterProfitPercentage: 0,
    plannedPassengers: 0,
    passengerPay: 0,
    userLocation: null,
    rangeCircleRadius: 500,
  });

  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstance = useRef<google.maps.Map | null>(null);
  const circleRef = useRef<google.maps.Circle | null>(null);
  const [columnFilters] = useState<ColumnFilter[]>([]);
  const [activeRankingColumn, setActiveRankingColumn] = useState<string>('bj');

  const [sortKey, setSortKey] = useState<keyof Jet>('multiYearTotalCost');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');

  const filteredJets = useMemo(() => {
    const filtered = jets
      .filter((jet: Jet) => {
        // Apply basic filters
        if (filters.range && jet.range < filters.range) return false;
        if (filters.passengers && jet.passengers < filters.passengers) return false;
        if (filters.averagePrice && jet.price > filters.averagePrice) return false;
        if (filters.lowestYearModel && jet.yearStart < filters.lowestYearModel) return false;

        // Apply range circle filter
        if (filters.rangeCircleRadius && jet.range < filters.rangeCircleRadius) return false;

        // Apply column filters
        for (const filter of columnFilters) {
          const jetValue = jet[filter.column as keyof Jet] as number | string;
          if (jetValue === undefined) continue;

          switch (filter.operator) {
            case 'eq':
              if (jetValue !== filter.value) return false;
              break;
            case 'gt':
              if (typeof jetValue === 'number' && typeof filter.value === 'number') {
                if (jetValue <= filter.value) return false;
              }
              break;
            case 'lt':
              if (typeof jetValue === 'number' && typeof filter.value === 'number') {
                if (jetValue >= filter.value) return false;
              }
              break;
            case 'gte':
              if (typeof jetValue === 'number' && typeof filter.value === 'number') {
                if (jetValue < filter.value) return false;
              }
              break;
            case 'lte':
              if (typeof jetValue === 'number' && typeof filter.value === 'number') {
                if (jetValue > filter.value) return false;
              }
              break;
            case 'contains':
              if (typeof jetValue === 'string' && typeof filter.value === 'string') {
                if (!jetValue.toLowerCase().includes(filter.value.toLowerCase())) return false;
              }
              break;
          }
        }

        return true;
      })
      .map((jet: Jet) => {
        // Calculate all metrics based on user inputs
        const jetWithMetrics = calculateJetMetrics(
          jet,
          filters.yearsOfOwnership,
          filters.averageTripLength,
          filters.numberOfTrips,
          filters.charterTripLength,
          filters.numberOfCharterTrips,
          filters.charterProfitPercentage,
          filters.userLocation,
          filters.rangeCircleRadius // Use the range radius for calculations
        );
        return jetWithMetrics;
      })
      .sort((a: Jet, b: Jet) => {
        const aValue = a[sortKey];
        const bValue = b[sortKey];
        if (aValue === undefined || bValue === undefined) return 0;
        return sortDirection === 'asc'
          ? (aValue < bValue ? -1 : 1)
          : (aValue > bValue ? -1 : 1);
      });

    return filtered;
  }, [filters, sortKey, sortDirection, columnFilters]);

  const nextStep = () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      setShowResults(true);
    }
  };

  const prevStep = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  // Initialize map function wrapped in useCallback
  const initMap = useCallback(() => {
    if (!mapRef.current) return;

    const defaultLocation = { lat: 37.7749, lng: -122.4194 }; // San Francisco
    const location = filters.userLocation || defaultLocation;

    // Create map instance
    const map = new window.google.maps.Map(mapRef.current, {
      center: location,
      zoom: 5,
    });

    mapInstance.current = map;

    // Create a marker for the user's location
    const marker = new window.google.maps.Marker({
      position: location,
      map: map,
      draggable: true,
      title: 'Your Location',
    });

    // Create a circle to represent the range
    const circle = new window.google.maps.Circle({
      strokeColor: '#F05545',
      strokeOpacity: 0.8,
      strokeWeight: 2,
      fillColor: '#F05545',
      fillOpacity: 0.35,
      map: map,
      center: location,
      radius: filters.rangeCircleRadius * 1852, // Convert nautical miles to meters
    });

    circleRef.current = circle;

    // Update circle when marker is dragged
    marker.addListener('dragend', () => {
      const newPos = marker.getPosition();
      if (newPos) {
        circle.setCenter(newPos);
        setFilters(prev => ({
          ...prev,
          userLocation: {
            lat: newPos.lat(),
            lng: newPos.lng(),
          }
        }));
      }
    });

    // Add search box
    const input = document.getElementById('location-search') as HTMLInputElement;
    if (input) {
      const searchBox = new window.google.maps.places.SearchBox(input);

      map.addListener('bounds_changed', () => {
        const bounds = map.getBounds();
        if (bounds) {
          searchBox.setBounds(bounds);
        }
      });

      searchBox.addListener('places_changed', () => {
        const places = searchBox.getPlaces();
        if (!places || places.length === 0) return;

        const place = places[0];
        // We already checked if place has geometry and location before using them
        if (!place || !place.geometry || !place.geometry.location) return;

        // Update marker and circle position
        marker.setPosition(place.geometry.location);
        circle.setCenter(place.geometry.location);

        // Update state
        setFilters(prev => ({
          ...prev,
          userLocation: {
            // Using non-null assertion operator since we checked above
            lat: place.geometry!.location!.lat(),
            lng: place.geometry!.location!.lng(),
          }
        }));

        // Pan to the location
        map.panTo(place.geometry.location);
        map.setZoom(8);
      });
    }
  }, [filters.userLocation, filters.rangeCircleRadius]);

  // Initialize map when on the range step
  useEffect(() => {
    if (steps[currentStep].hasMap && typeof window !== 'undefined') {
      // Load Google Maps API if not already loaded
      if (!window.google) {
        const script = document.createElement('script');
        script.src = `https://maps.googleapis.com/maps/api/js?key=YOUR_API_KEY&libraries=places`;
        script.async = true;
        script.defer = true;
        script.onload = initMap;
        document.head.appendChild(script);
      } else {
        initMap();
      }
    }
  }, [currentStep, initMap]);

  // Update circle radius when rangeRadius changes
  useEffect(() => {
    if (circleRef.current) {
      circleRef.current.setRadius(filters.rangeCircleRadius * 1852); // Convert nautical miles to meters
    }
  }, [filters.rangeCircleRadius]);

  const toggleJetSelection = (jet: Jet) => {
    setSelectedJets(prev => {
      const isSelected = prev.some(j => j.model === jet.model);
      if (isSelected) {
        return prev.filter(j => j.model !== jet.model);
      } else {
        return [...prev, jet];
      }
    });
  };

  const compareSelectedJets = () => {
    if (selectedJets.length > 0) {
      setShowComparison(true);
    }
  };

  const closeComparison = () => {
    setShowComparison(false);
  };

  return (
    <div className="min-h-screen bg-jet-black text-jet-white">
      {/* Header with JETSCHOOL logo */}
      <header className="bg-jet-black p-4 shadow-md">
        <div className="container mx-auto flex justify-between items-center">
          <img src={jetschoolLogo} alt="JETSCHOOL" className="h-12" />
          <h1 className="text-2xl font-bold text-jet-white">Jet Finder</h1>
        </div>
      </header>

      {/* Main content */}
      <main className="container mx-auto p-4">
        {!showResults ? (
          <div className="max-w-3xl mx-auto bg-jet-black rounded-xl shadow-lg overflow-hidden border border-gray-800">
            <div className="p-6">
              <div className="mb-8">
                <h2 className="text-2xl font-semibold text-jet-white mb-4">Find Your Perfect Jet</h2>
                <p className="text-gray-300">Enter your requirements to find the best aircraft for your needs.</p>
              </div>

              {/* Step indicator */}
              <div className="flex justify-between mb-8">
                {[1, 2, 3, 4].map((stepNum) => (
                  <div
                    key={stepNum}
                    className={`w-1/4 text-center relative ${currentStep >= stepNum ? 'text-jet-red' : 'text-gray-500'
                      }`}
                  >
                    <div
                      className={`h-2 absolute top-1/2 w-full -translate-y-1/2 ${stepNum === 1 ? 'hidden' : ''
                        } ${currentStep >= stepNum ? 'bg-jet-red' : 'bg-gray-700'
                        }`}
                      style={{ right: '50%' }}
                    ></div>
                    <div
                      className={`h-2 absolute top-1/2 w-full -translate-y-1/2 ${stepNum === 4 ? 'hidden' : ''
                        } ${currentStep > stepNum ? 'bg-jet-red' : 'bg-gray-700'
                        }`}
                      style={{ left: '50%' }}
                    ></div>
                    <div
                      className={`w-8 h-8 mx-auto rounded-full flex items-center justify-center mb-2 ${currentStep >= stepNum ? 'bg-jet-red text-white' : 'bg-gray-700 text-gray-400'
                        }`}
                    >
                      {stepNum}
                    </div>
                    <div className="text-sm">
                      {stepNum === 1 && 'Basic Info'}
                      {stepNum === 2 && 'Usage'}
                      {stepNum === 3 && 'Charter'}
                      {stepNum === 4 && 'Passengers'}
                    </div>
                  </div>
                ))}
              </div>

              {/* Form content */}
              <div className="space-y-6">
                {steps[currentStep].hasMap && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Search for your location
                    </label>
                    <input
                      id="location-search"
                      type="text"
                      className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors mb-4"
                      placeholder="Enter your location"
                    />
                    <div
                      ref={mapRef}
                      className="w-full h-64 rounded-lg border border-gray-300 mb-4"
                    ></div>
                    <p className="text-sm text-gray-500 mb-4">
                      Drag the marker to set your location. The circle represents your range.
                    </p>
                  </div>
                )}

                {steps[currentStep].fields.map((field) => (
                  <div key={field}>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      {fieldLabels[field]}
                    </label>
                    <input
                      type="number"
                      className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                      value={filters[field as keyof Filters] as number || ''}
                      onChange={e => {
                        const value = Number(e.target.value);
                        setFilters(prev => ({ ...prev, [field]: value }));
                      }}
                      min={0}
                    />
                  </div>
                ))}
              </div>

              {/* Navigation buttons */}
              <div className="flex justify-between mt-8">
                {currentStep > 1 && (
                  <button
                    onClick={prevStep}
                    className="bg-gray-800 hover:bg-gray-700 text-white px-6 py-2 rounded-md"
                  >
                    Back
                  </button>
                )}
                <div className="ml-auto">
                  {currentStep < 4 ? (
                    <button
                      onClick={nextStep}
                      className="bg-jet-red hover:bg-opacity-90 text-white px-6 py-2 rounded-md"
                    >
                      Next
                    </button>
                  ) : (
                    <button
                      onClick={() => setShowResults(true)}
                      className="bg-jet-red hover:bg-opacity-90 text-white px-6 py-2 rounded-md"
                    >
                      Find Jets
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="bg-jet-black rounded-xl shadow-lg overflow-hidden border border-gray-800">
            <div className="p-6">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-semibold text-jet-white">Results</h2>
                <button
                  onClick={() => setShowResults(false)}
                  className="bg-gray-800 hover:bg-gray-700 text-white px-4 py-2 rounded-md"
                >
                  Back to Search
                </button>
              </div>

              {/* Results section */}
              {showComparison ? (
                <>
                  <div className="flex justify-between items-center mb-6">
                    <h3 className="text-xl font-semibold text-jet-white">Comparing {selectedJets.length} Jets</h3>
                    <button
                      onClick={closeComparison}
                      className="bg-gray-800 hover:bg-gray-700 text-white px-4 py-2 rounded-md"
                    >
                      Back to Results
                    </button>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full border-collapse">
                      <thead>
                        <tr className="bg-gray-900">
                          <th className="p-3 text-left text-jet-white">Specification</th>
                          {selectedJets.map(jet => (
                            <th key={jet.model} className="p-3 text-left text-jet-white">{jet.model}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {[
                          { key: 'manufacturer', label: 'Manufacturer' },
                          { key: 'type', label: 'Type' },
                          { key: 'yearStart', label: 'Year' },
                          { key: 'price', label: 'Price', format: (val: number) => `$${(val / 1000000).toFixed(1)}M` },
                          { key: 'range', label: 'Range', format: (val: number) => `${val.toLocaleString()} nm` },
                          { key: 'cruiseSpeed', label: 'Cruise Speed', format: (val: number) => `${val} kts` },
                          { key: 'passengers', label: 'Passengers' },
                          { key: 'totalHourlyCost', label: 'Hourly Cost', format: (val: number) => `$${val.toLocaleString()}` },
                          { key: 'multiYearTotalCost', label: 'Total Cost of Ownership', format: (val: number) => `$${(val / 1000000).toFixed(1)}M` },
                          { key: 'as', label: 'AS Score', format: (val: number) => val.toFixed(2) },
                          { key: 'ax', label: 'AX Score', format: (val: number) => val.toFixed(2) },
                          { key: 'ba', label: 'BA Score', format: (val: number) => val.toFixed(2) },
                          { key: 'bd', label: 'BD Score', format: (val: number) => val.toFixed(2) },
                          { key: 'bg', label: 'BG Score', format: (val: number) => val.toFixed(2) },
                          { key: 'bj', label: 'BJ Score', format: (val: number) => val.toFixed(2) }
                        ].map(row => (
                          <tr key={row.key} className="border-b border-gray-800">
                            <td className="px-3 py-2 text-sm font-medium text-jet-white">
                              {row.label}
                            </td>
                            {selectedJets.map(jet => (
                              <td key={`${jet.model}-${row.key}`} className="px-3 py-2 text-sm text-gray-300">
                                {row.format
                                  ? row.format(jet[row.key as keyof Jet] as number || 0)
                                  : jet[row.key as keyof Jet] || '-'}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </>
              ) : (
                <>
                  <div className="flex justify-between items-center mb-6">
                    <h2 className="text-2xl font-semibold text-jet-white">Aircraft Rankings</h2>
                    <div className="flex space-x-4">
                      <button
                        onClick={compareSelectedJets}
                        disabled={selectedJets.length === 0}
                        className={`px-4 py-2 rounded-md text-sm font-medium transition-colors
                          ${selectedJets.length === 0
                            ? 'bg-gray-800 text-gray-500 cursor-not-allowed'
                            : 'bg-jet-red text-white hover:bg-opacity-90'}`}
                      >
                        Compare Selected ({selectedJets.length})
                      </button>
                    </div>
                  </div>

                  {/* Ranking column selector */}
                  <div className="mb-6">
                    <h3 className="text-lg font-semibold text-jet-white mb-2">Rank By:</h3>
                    <div className="flex flex-wrap gap-2">
                      {rankingColumns.map(column => (
                        <button
                          key={column.key}
                          onClick={() => {
                            setActiveRankingColumn(column.key);
                            setSortKey(column.key as keyof Jet);
                            setSortDirection('desc');
                          }}
                          className={`px-3 py-1 text-sm rounded-full transition-colors ${activeRankingColumn === column.key
                            ? 'bg-jet-red text-white'
                            : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                            }`}
                        >
                          {column.label}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Results count */}
                  <p className="text-gray-300 mb-4">Found {filteredJets.length} matching aircraft</p>

                  {/* Results grid */}
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {filteredJets.map((jet: Jet, index: number) => (
                      <div
                        key={jet.model}
                        className={`bg-gray-900 rounded-lg overflow-hidden shadow-lg border ${selectedJets.some(j => j.model === jet.model)
                          ? 'border-jet-red'
                          : 'border-gray-800'
                          }`}
                      >
                        <div className="p-4">
                          <div className="flex justify-between items-start">
                            <div>
                              <div className="flex items-center">
                                <span className="bg-jet-red text-white text-sm font-bold rounded-full w-6 h-6 flex items-center justify-center mr-2">
                                  {index + 1}
                                </span>
                                <h3 className="text-xl font-semibold text-jet-white">{jet.model}</h3>
                              </div>
                              <p className="text-gray-400">{jet.manufacturer} • {jet.type}</p>
                              <p className="text-gray-400">Year: {jet.yearStart}-{jet.yearEnd}</p>
                            </div>
                            <button
                              onClick={() => toggleJetSelection(jet)}
                              className={`p-2 rounded-full ${selectedJets.some(j => j.model === jet.model)
                                ? 'bg-jet-red text-white'
                                : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                                }`}
                            >
                              {selectedJets.some(j => j.model === jet.model) ? '✓' : '+'}
                            </button>
                          </div>
                        </div>

                        <div className="border-t border-gray-800 p-4">
                          <div className="grid grid-cols-2 gap-4">
                            <div>
                              <p className="text-gray-400 text-sm">Price</p>
                              <p className="text-jet-white font-semibold">${(jet.price / 1000000).toFixed(1)}M</p>
                            </div>
                            <div>
                              <p className="text-gray-400 text-sm">Range</p>
                              <p className="text-jet-white font-semibold">{jet.range} nm</p>
                            </div>
                            <div>
                              <p className="text-gray-400 text-sm">Speed</p>
                              <p className="text-jet-white font-semibold">{jet.cruiseSpeed} kts</p>
                            </div>
                            <div>
                              <p className="text-gray-400 text-sm">Passengers</p>
                              <p className="text-jet-white font-semibold">{jet.passengers}</p>
                            </div>
                          </div>
                        </div>

                        <div className="border-t border-gray-800 p-4">
                          <div className="space-y-2">
                            <div>
                              <p className="text-gray-400 text-sm">{rankingColumns.find(c => c.key === activeRankingColumn)?.label || 'Score'}</p>
                              <p className="text-jet-white font-semibold">
                                {((jet[activeRankingColumn as keyof Jet] as number) || 0).toFixed(2)}
                              </p>
                            </div>
                            <div>
                              <p className="text-gray-400 text-sm">Ranking</p>
                              <div className="w-full bg-gray-800 rounded-full h-2.5">
                                <div
                                  className="bg-jet-red h-2.5 rounded-full"
                                  style={{
                                    width: `${100 - (index / Math.max(filteredJets.length - 1, 1)) * 100}%`
                                  }}
                                ></div>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-jet-black p-4 border-t border-gray-800">
        <div className="container mx-auto text-center text-jet-white">
          <p>© {new Date().getFullYear()} JETSCHOOL. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}

export default App