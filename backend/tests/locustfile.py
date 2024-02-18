from locust import HttpUser, task


class StressTestAPI(HttpUser):
    @task
    def pokemon_detailed(self):
        self.client.get("/api/pokemon-detailed/")

    @task
    def pokemon(self):
        self.client.get("/api/pokemon/")
