const API_URL = "http://localhost:5003";


// ---------------------------------------------------------
// Submit Application
// ---------------------------------------------------------

document
    .getElementById("applicationForm")
    .addEventListener("submit", async function(event) {

        event.preventDefault();

        const citizen_id =
            parseInt(
                document.getElementById("citizen_id").value
            );

        const ration_card =
            document.getElementById("ration_card").value;

        const annual_income =
            parseFloat(
                document.getElementById("annual_income").value
            );

        const is_household_head =
            document.getElementById("is_household_head").value === "true";


        try {

            const response = await fetch(
                `${API_URL}/applications`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type": "application/json"
                    },

                    body: JSON.stringify({
                        citizen_id,
                        ration_card,
                        annual_income,
                        is_household_head
                    })
                }
            );


            const data = await response.json();

            displayResult(data);

        }

        catch (error) {

            displayResult({
                error: "Unable to connect to Gruha Lakshmi Service"
            });

        }

    });


// ---------------------------------------------------------
// Get Application
// ---------------------------------------------------------

async function getApplication() {

    const applicationId =
        document.getElementById(
            "application_id"
        ).value;


    if (!applicationId) {

        displayResult({
            error: "Enter an application ID"
        });

        return;
    }


    try {

        const response = await fetch(
            `${API_URL}/applications/${applicationId}`
        );

        const data = await response.json();

        displayResult(data);

    }

    catch (error) {

        displayResult({
            error: "Unable to connect to service"
        });

    }
}


// ---------------------------------------------------------
// Make Payment
// ---------------------------------------------------------

async function makePayment() {

    const applicationId =
        document.getElementById(
            "payment_application_id"
        ).value;


    if (!applicationId) {

        displayResult({
            error: "Enter an application ID"
        });

        return;
    }


    try {

        const response = await fetch(
            `${API_URL}/applications/${applicationId}/payment`,
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({})
            }
        );


        const data = await response.json();

        displayResult(data);

    }

    catch (error) {

        displayResult({
            error: "Unable to connect to service"
        });

    }
}


// ---------------------------------------------------------
// Display Result
// ---------------------------------------------------------

function displayResult(data) {

    document.getElementById("result").innerHTML = `
        <div class="result-card">
            <h2>Result</h2>

            <pre>${JSON.stringify(
                data,
                null,
                2
            )}</pre>
        </div>
    `;
}