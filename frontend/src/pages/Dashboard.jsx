import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../lib/supabase-auth";
import { Link } from "react-router-dom";

const fetchMyListings = async () => {
  const { data } = await apiClient.get("/api/listings?my_listings=true");
  return data.listings || [];
};

export default function Dashboard() {
  const { data: listings, isLoading } = useQuery({
    queryKey: ["my-listings"],
    queryFn: fetchMyListings,
  });

  const getStatusBadge = (status) => {
    const colors = {
      pending: "bg-yellow-100 text-yellow-800",
      active: "bg-green-100 text-green-800",
      rejected: "bg-red-100 text-red-800",
    };
    return (
      <span
        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
          colors[status] || "bg-gray-100 text-gray-800"
        }`}
      >
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    );
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">My Dashboard</h1>
        <p className="mt-2 text-sm text-gray-600">
          Manage your aircraft listings and view your account information.
        </p>
      </div>

      <div className="mb-6">
        <Link
          to="/sell"
          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700"
        >
          Create New Listing
        </Link>
      </div>

      <div className="bg-white shadow overflow-hidden sm:rounded-md">
        <ul className="divide-y divide-gray-200">
          {isLoading ? (
            <li className="px-6 py-8 text-center text-gray-500">Loading...</li>
          ) : listings?.length === 0 ? (
            <li className="px-6 py-8 text-center text-gray-500">
              No listings yet.{" "}
              <Link to="/sell" className="text-indigo-600 hover:text-indigo-500">
                Create your first listing
              </Link>
            </li>
          ) : (
            listings?.map((listing) => (
              <li key={listing.id}>
                <Link
                  to={`/listings/${listing.id}`}
                  className="block hover:bg-gray-50 px-6 py-4"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center">
                        <h3 className="text-lg font-medium text-gray-900">{listing.title}</h3>
                        <div className="ml-3">{getStatusBadge(listing.status)}</div>
                      </div>
                      <div className="mt-1 text-sm text-gray-500">
                        {listing.location} • ${listing.price_usd.toLocaleString()}
                      </div>
                      <div className="mt-1 text-xs text-gray-400">
                        Created {new Date(listing.created_at * 1000).toLocaleDateString()}
                      </div>
                    </div>
                    <div className="ml-4 flex-shrink-0">
                      <svg
                        className="h-5 w-5 text-gray-400"
                        fill="currentColor"
                        viewBox="0 0 20 20"
                      >
                        <path
                          fillRule="evenodd"
                          d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"
                          clipRule="evenodd"
                        />
                      </svg>
                    </div>
                  </div>
                </Link>
              </li>
            ))
          )}
        </ul>
      </div>
    </div>
  );
}

