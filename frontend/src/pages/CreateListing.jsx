import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { apiClient } from "../lib/supabase-auth";

const fetchProfiles = async () => {
    const { data } = await apiClient.get("/api/profiles");
    return data.profiles || [];
};

const fetchPlans = async () => {
    const { data } = await apiClient.get("/api/profiles/plans");
    return data.plans || [];
};

const createListing = async (payload) => {
    const { data } = await apiClient.post("/api/listings", payload);
    return data;
};

export default function CreateListing() {
    const navigate = useNavigate();
    const queryClient = useQueryClient();
    const { data: profiles, isLoading: profilesLoading } = useQuery({ 
        queryKey: ["profiles"], 
        queryFn: fetchProfiles 
    });
    const { data: plans, isLoading: plansLoading } = useQuery({ 
        queryKey: ["plans"], 
        queryFn: fetchPlans 
    });
    const [submissionState, setSubmissionState] = useState({ status: "idle", message: "" });

    const {
        register,
        handleSubmit,
        reset,
        formState: { isSubmitting }
    } = useForm({
        defaultValues: {
            title: "",
            price_usd: 0,
            location: "",
            engine_type: "",
            contact_email: "",
            description: "",
            performance_profile_id: "",
            payment_plan: "monthly"
        }
    });

    const mutation = useMutation({
        mutationFn: createListing,
        onSuccess: (data) => {
            queryClient.invalidateQueries({ queryKey: ["listings"] });
            queryClient.invalidateQueries({ queryKey: ["my-listings"] });
            queryClient.invalidateQueries({ queryKey: ["pending-listings"] });
            setSubmissionState({
                status: "success",
                message: `${data.listing?.title || 'Listing'} submitted for admin review. You'll be notified once it's approved.`
            });
            reset();
            // Redirect to dashboard after 3 seconds
            setTimeout(() => {
                navigate("/dashboard");
            }, 3000);
        },
        onError: (error) => {
            setSubmissionState({
                status: "error",
                message: error.response?.data?.error || "Unable to submit listing. Please verify your entries and try again."
            });
        }
    });

    const onSubmit = (values) => {
        setSubmissionState({ status: "idle", message: "" });
        const payload = {
            title: values.title,
            description: values.description || "",
            price_usd: Number(values.price_usd),
            location: values.location,
            engine_type: values.engine_type,
            contact_email: values.contact_email,
            serial_number: values.serial_number || "",
            hours: values.hours ? Number(values.hours) : null,
            year: values.year ? Number(values.year) : null,
            performance_profile_id: Number(values.performance_profile_id),
            pricing_plan_id: Number(values.pricing_plan_id),
        };
        mutation.mutate(payload);
    };

    return (
        <section className="mx-auto max-w-3xl space-y-6">
            <header>
                <h1 className="text-3xl font-semibold">Create Listing</h1>
                <p className="mt-2 text-slate-400">
                    Select a performance profile, enter pricing/location info, and submit for admin review.
                </p>
            </header>

            {submissionState.status !== "idle" && (
                <div
                    className={`rounded-xl border px-4 py-3 text-sm ${submissionState.status === "success"
                            ? "border-green-500/40 bg-green-500/10 text-green-200"
                            : "border-red-500/40 bg-red-500/10 text-red-200"
                        }`}
                >
                    {submissionState.message}
                </div>
            )}

            <form
                className="space-y-6 rounded-2xl border border-slate-800 bg-slate-900/60 p-6 shadow"
                onSubmit={handleSubmit(onSubmit)}
            >
                {profilesLoading ? (
                    <div className="text-slate-400">Loading performance profiles...</div>
                ) : (
                    <div>
                        <label className="text-sm font-medium text-slate-300">
                            Performance Profile <span className="text-red-400">*</span>
                        </label>
                        <select
                            {...register("performance_profile_id", { required: true })}
                            className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-white"
                        >
                            <option value="">Select profile</option>
                            {profiles?.map((profile) => (
                                <option key={profile.id} value={profile.id}>
                                    {profile.manufacturer} {profile.name}
                                </option>
                            ))}
                        </select>
                    </div>
                )}

                <div>
                    <label className="text-sm font-medium text-slate-300">
                        Listing Name <span className="text-red-400">*</span>
                    </label>
                    <input
                        type="text"
                        {...register("title", { required: true })}
                        placeholder="e.g., 2018 Cessna Citation CJ3+ - Low Hours"
                        className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-white"
                    />
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                    <div>
                        <label className="text-sm font-medium text-slate-300">
                            Serial Number <span className="text-red-400">*</span>
                        </label>
                        <input
                            type="text"
                            {...register("serial_number", { required: true })}
                            placeholder="e.g., 525C-0123"
                            className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-white"
                        />
                    </div>
                    <div>
                        <label className="text-sm font-medium text-slate-300">
                            Total Time (Hours) <span className="text-red-400">*</span>
                        </label>
                        <input
                            type="number"
                            {...register("hours", { required: true, min: 0 })}
                            placeholder="1250"
                            className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-white"
                        />
                    </div>
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                    <div>
                        <label className="text-sm font-medium text-slate-300">
                            Year Model <span className="text-red-400">*</span>
                        </label>
                        <input
                            type="number"
                            {...register("year", { required: true, min: 1950, max: 2030 })}
                            placeholder="2018"
                            className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-white"
                        />
                    </div>
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                    <div>
                        <label className="text-sm font-medium text-slate-300">Asking Price (USD)</label>
                        <input
                            type="number"
                            {...register("price_usd", { required: true })}
                            className="mt-2 w-full rounded-lg border border-slate-700 bg-transparent px-3 py-2"
                        />
                    </div>
                    <div>
                        <label className="text-sm font-medium text-slate-300">Location (Airport Code)</label>
                        <input
                            {...register("location", { required: true })}
                            className="mt-2 w-full rounded-lg border border-slate-700 bg-transparent px-3 py-2"
                        />
                    </div>
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                    <div>
                        <label className="text-sm font-medium text-slate-300">Engine Type</label>
                        <input
                            {...register("engine_type", { required: true })}
                            className="mt-2 w-full rounded-lg border border-slate-700 bg-transparent px-3 py-2"
                        />
                    </div>
                    <div>
                        <label className="text-sm font-medium text-slate-300">Contact Email</label>
                        <input
                            type="email"
                            {...register("contact_email", { required: true })}
                            className="mt-2 w-full rounded-lg border border-slate-700 bg-transparent px-3 py-2"
                        />
                    </div>
                </div>

                {plansLoading ? (
                    <div className="text-slate-400">Loading pricing plans...</div>
                ) : (
                    <div>
                        <label className="text-sm font-medium text-slate-300">
                            Pricing Plan <span className="text-red-400">*</span>
                        </label>
                        <div className="mt-2 flex flex-col gap-2 md:flex-row md:gap-6">
                            {plans?.map((plan) => (
                                <label key={plan.id} className="flex items-center gap-2 text-sm text-slate-300 cursor-pointer">
                                    <input 
                                        type="radio" 
                                        value={plan.id} 
                                        {...register("pricing_plan_id", { required: true })} 
                                        className="cursor-pointer"
                                    />
                                    {plan.name} (${plan.price_usd}/{plan.billing_cycle_months === 1 ? "mo" : `${plan.billing_cycle_months} mo`})
                                </label>
                            ))}
                        </div>
                    </div>
                )}

                <div>
                    <label className="text-sm font-medium text-slate-300">Description</label>
                    <textarea
                        rows="4"
                        {...register("description")}
                        placeholder="Optional: Additional details about the aircraft..."
                        className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-white"
                    />
                </div>

                <button
                    type="submit"
                    disabled={isSubmitting || mutation.isPending}
                    className="w-full rounded-xl bg-brand-500 py-3 font-semibold text-white transition hover:bg-brand-600 disabled:opacity-50"
                >
                    Submit for Review
                </button>
            </form>
        </section>
    );
}

