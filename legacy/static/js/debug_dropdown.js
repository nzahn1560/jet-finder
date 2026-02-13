// Debug script to check dropdown visibility
console.log('🔍 DEBUG: Checking dropdown elements...');

document.addEventListener('DOMContentLoaded', function () {
    setTimeout(() => {
        console.log('🔍 Checking home airport elements...');

        const homeInput = document.getElementById('home-airport-search');
        const homeResults = document.getElementById('home-airport-results');
        const homeList = document.getElementById('home-airport-list');

        console.log('Elements found:', {
            homeInput: !!homeInput,
            homeResults: !!homeResults,
            homeList: !!homeList
        });

        if (homeResults) {
            const computedStyle = window.getComputedStyle(homeResults);
            console.log('Home results element details:', {
                classList: Array.from(homeResults.classList),
                inlineStyle: homeResults.style.cssText,
                computedDisplay: computedStyle.display,
                computedPosition: computedStyle.position,
                computedZIndex: computedStyle.zIndex,
                computedTop: computedStyle.top,
                computedLeft: computedStyle.left,
                computedVisibility: computedStyle.visibility,
                computedOpacity: computedStyle.opacity,
                parentElement: homeResults.parentElement?.tagName,
                clientRect: homeResults.getBoundingClientRect(),
                offsetParent: homeResults.offsetParent?.tagName || 'null'
            });
        }

        if (homeInput) {
            console.log('Adding test input listener...');
            homeInput.addEventListener('input', function () {
                console.log('🔍 Test input triggered:', this.value);

                if (this.value.trim().length >= 2) {
                    // Manually show the dropdown for testing
                    if (homeResults) {
                        console.log('🔍 Attempting to show dropdown...');
                        homeResults.classList.remove('d-none');
                        homeResults.style.display = 'block';
                        homeResults.style.position = 'absolute';
                        homeResults.style.top = '100%';
                        homeResults.style.left = '0';
                        homeResults.style.right = '0';
                        homeResults.style.zIndex = '9999';
                        homeResults.style.background = '#ff0000'; // Red background for testing
                        homeResults.style.border = '2px solid yellow';

                        if (homeList) {
                            homeList.innerHTML = `
                                <div style="padding: 10px; color: white; background: green;">
                                    TEST DROPDOWN IS WORKING!<br>
                                    Query: "${this.value}"
                                </div>
                            `;
                        }

                        console.log('🔍 Dropdown should now be visible with red background');
                    }
                }
            });
        }
    }, 1000);
}); 